
with top_rh as(
    select symbol,
           cost_basis,
           market_value,
           total_return_pct,
           source,
           last_updated_est
    from merged_positions
    where source = "robinhood"
    order by market_value desc
    limit 10
),


top_vg as(
    select symbol,
           cost_basis,
           market_value,
           total_return_pct,
           source,
           last_updated_est
    from merged_positions
    where source = "vanguard"
    order by market_value desc
    limit 5
),

combined as(
    select * from top_rh
    UNION ALL
    select * from top_vg)

select * from combined
order by total_return_pct desc
