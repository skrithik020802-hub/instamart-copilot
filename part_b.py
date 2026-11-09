import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import confusion_matrix, classification_report, f1_score
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

os.makedirs("outputs", exist_ok=True)

orders = pd.read_csv("data/clean/orders.csv")
customers = pd.read_csv("data/clean/customers.csv")
products = pd.read_csv("data/clean/products.csv")

# 1. RFM
comp = orders[orders['status'] == 'completed'].copy()
comp['order_ts'] = pd.to_datetime(comp['order_ts'])
snapshot = pd.to_datetime('2025-10-01 00:00:00')

rfm = comp.groupby('customer_id').agg(
    last_order=('order_ts', 'max'),
    frequency=('order_id', 'nunique'),
    monetary=('order_amount', 'sum')
).reset_index()

rfm['recency'] = (snapshot - rfm['last_order']).dt.days
rfm = rfm[['customer_id', 'recency', 'frequency', 'monetary']]

# 2. KMeans (K=4)
scaler = StandardScaler()
scaled_rfm = scaler.fit_transform(rfm[['recency', 'frequency', 'monetary']])
kmeans = KMeans(n_clusters=4, n_init=10, random_state=42).fit(scaled_rfm)
rfm['segment_id'] = kmeans.labels_

# Profile segments
seg_means = rfm.groupby('segment_id')['monetary'].mean()
prem_id = seg_means.idxmax()
rfm['is_premium'] = rfm['segment_id'] == prem_id
rfm['segment_name'] = rfm['segment_id'].map({prem_id: 'Premium', 0: 'Regular', 1: 'At-Risk', 2: 'Casual', 3: 'Loyal'})

pca = PCA(n_components=2, random_state=42)
pca_res = pca.fit_transform(scaled_rfm)

rfm.to_csv("outputs/customer_segments.csv", index=False)

# 4. Lapse model
cutoff = pd.to_datetime('2025-09-01')
pre_orders = orders[pd.to_datetime(orders['order_ts']) < cutoff].copy()
pre_comp = pre_orders[pre_orders['status'] == 'completed']

# Cohort
cohort = pre_comp['customer_id'].unique()
sept_comp = orders[(pd.to_datetime(orders['order_ts']) >= cutoff) & 
                   (pd.to_datetime(orders['order_ts']) <= pd.to_datetime('2025-09-30')) & 
                   (orders['status'] == 'completed')]
active_sept = set(sept_comp['customer_id'])

df_lapse = pd.DataFrame({'customer_id': cohort})
df_lapse['lapsed'] = df_lapse['customer_id'].apply(lambda x: 0 if x in active_sept else 1)

# Features pre-cutoff
feat_rec = pre_comp.groupby('customer_id')['order_ts'].max().reset_index()
feat_rec['recency'] = (cutoff - pd.to_datetime(feat_rec['order_ts'])).dt.days
feat_freq = pre_comp.groupby('customer_id')['order_id'].nunique().reset_index().rename(columns={'order_id': 'frequency'})
feat_mon = pre_comp.groupby('customer_id')['order_amount'].sum().reset_index().rename(columns={'order_amount': 'monetary'})
feat_disc = pre_comp.groupby('customer_id')['discount_pct'].mean().reset_index().rename(columns={'discount_pct': 'avg_discount_pct'})
feat_deliv = pre_comp.groupby('customer_id')['delivery_minutes'].mean().reset_index().rename(columns={'delivery_minutes': 'avg_delivery_minutes'})

# Cancellation rate
all_pre_final = pre_orders[pre_orders['status'].isin(['completed', 'cancelled'])]
canc = all_pre_final.groupby('customer_id')['status'].apply(lambda s: (s == 'cancelled').sum() / len(s)).reset_index().rename(columns={'status': 'cancellation_rate'})

# Favorite category
pre_comp_p = pre_comp.merge(products[['product_id', 'category']], on='product_id', how='left')
fav_cat = pre_comp_p.groupby(['customer_id', 'category']).size().reset_index(name='cnt')
fav_cat = fav_cat.sort_values('cnt', ascending=False).drop_duplicates('customer_id')[['customer_id', 'category']].rename(columns={'category': 'frequent_category'})

# Merge features
df_feat = df_lapse.merge(customers[['customer_id', 'city', 'age', 'gender', 'signup_date']], on='customer_id', how='left')
df_feat['tenure'] = (cutoff - pd.to_datetime(df_feat['signup_date'])).dt.days
df_feat = df_feat.merge(feat_rec[['customer_id', 'recency']], on='customer_id', how='left')
df_feat = df_feat.merge(feat_freq, on='customer_id', how='left')
df_feat = df_feat.merge(feat_mon, on='customer_id', how='left')
df_feat = df_feat.merge(feat_disc, on='customer_id', how='left')
df_feat = df_feat.merge(canc, on='customer_id', how='left')
df_feat = df_feat.merge(feat_deliv, on='customer_id', how='left')
df_feat = df_feat.merge(fav_cat, on='customer_id', how='left')

X = df_feat.drop(columns=['customer_id', 'lapsed', 'signup_date'])
y = df_feat['lapsed']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

cat_cols = ['city', 'gender', 'frequent_category']
num_cols = [c for c in X.columns if c not in cat_cols]

preprocessor = ColumnTransformer(transformers=[
    ('num', StandardScaler(), num_cols),
    ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), cat_cols)
])

clf = Pipeline(steps=[('preprocessor', preprocessor),
                      ('classifier', RandomForestClassifier(n_estimators=100, max_depth=8, min_samples_leaf=10, random_state=42))])

clf.fit(X_train, y_train)
joblib.dump(clf, "outputs/lapse_model.joblib")

# Retention list
test_preds = clf.predict_proba(X_test)[:, 1]
ret_df = pd.DataFrame({'customer_id': df_feat.loc[X_test.index, 'customer_id'], 'lapse_probability': test_preds})
ret_df = ret_df.merge(rfm[['customer_id', 'is_premium']], on='customer_id', how='left')
ret_df.sort_values('lapse_probability', ascending=False).to_csv("outputs/retention_list.csv", index=False)

print("Part B complete.")
