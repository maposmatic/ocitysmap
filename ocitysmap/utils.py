
def gen_vertical_square_label(x):
    label = ''
    while x != -1:
        label = chr(ord('A') + x % 26) + label
        x /= 26
        x -= 1
    return label

def gen_horizontal_square_label(x):
    return str(x + 1)
