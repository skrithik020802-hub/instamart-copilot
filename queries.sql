-- Q1: WHERE then HAVING (Completed orders > 500, total customer spend > 8000)
SELECT customer_id, SUM(order_amount) AS total_spend
FROM orders
WHERE status = 'completed' AND order_amount > 500
GROUP BY customer_id
HAVING SUM(order_amount) > 8000;

-- Q2: Three-table join (Revenue by city and product category)
SELECT c.city, p.category, SUM(o.order_amount) AS total_revenue
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
WHERE o.status = 'completed'
GROUP BY c.city, p.category;

-- Q3: Scalar subquery (Products priced above average catalogue price)
SELECT product_name, price_inr
FROM products
WHERE price_inr > (SELECT AVG(price_inr) FROM products);

-- Q4: LEFT JOIN (Customers with no completed orders)
SELECT c.customer_id, c.city
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'completed'
WHERE o.order_id IS NULL;

-- Q5: Common Table Expression (Customers spending above average total spend)
WITH customer_spend AS (
    SELECT customer_id, SUM(order_amount) AS total_spend
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
avg_spend AS (
    SELECT AVG(total_spend) AS overall_avg FROM customer_spend
)
SELECT cs.customer_id, cs.total_spend
FROM customer_spend cs, avg_spend
WHERE cs.total_spend > avg_spend.overall_avg;

-- Q6: Ranking window functions
SELECT customer_id, city, total_spend,
       RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) as rank_num,
       DENSE_RANK() OVER (PARTITION BY city ORDER BY total_spend DESC) as dense_rank_num,
       ROW_NUMBER() OVER (PARTITION BY city ORDER BY total_spend DESC) as row_num
FROM (
    SELECT c.customer_id, c.city, SUM(o.order_amount) AS total_spend
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.status = 'completed'
    GROUP BY c.customer_id, c.city
);

-- Q7: Running total of daily completed revenue
SELECT SUBSTR(order_ts, 1, 10) AS order_date,
       SUM(order_amount) AS daily_revenue,
       SUM(SUM(order_amount)) OVER (ORDER BY SUBSTR(order_ts, 1, 10)) AS cumulative_revenue
FROM orders
WHERE status = 'completed'
GROUP BY SUBSTR(order_ts, 1, 10);
