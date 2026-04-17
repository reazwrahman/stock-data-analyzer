with worst_performers as(
    select symbol,
           quantity,
           current_price,
           cost_basis,
           market_value,
           total_return,
           total_return_pct,
           source,
           last_updated_est
    from merged_positions
    where
        source = "robinhood"
--         source = "vanguard"
      and total_return_pct < -10
      and market_value > 250
    order by market_value desc
--     limit 8
)
select
--     SUM(total_return),
--     SUM(market_value)
        *
from worst_performers;