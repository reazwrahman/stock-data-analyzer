def calculate_cost(curr_value, delta, direction): 
    curr_value = float(curr_value.replace(",",""))
    delta = float(delta.replace(",",""))

    cost = None
    if direction == "up":
        cost = curr_value - delta
    else:
        cost = curr_value + delta

    return cost 

print(calculate_cost("28,147.70","28000","up"))