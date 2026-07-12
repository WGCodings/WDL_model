def normalize_eval(raw_eval,mom):
    constants = [-125.64805429, 571.08702719, -890.10447358, 805.61056096]

    return raw_eval/(((constants[0]*mom/32 + constants[1])*mom/32 + constants[2])*mom/32 + constants[3])


x = normalize_eval(0,78)

print(x)