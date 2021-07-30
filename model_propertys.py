# 将首字母转换为小写
def small_str(s):
    if len(s) <= 1:
        return s
    return (s[0:1]).lower() + s[1:]

# 将首字母转换为大写
def large_str(s):
    s = s.lower()
    if len(s) <= 1:
        return s.upper()
    return (s[0:1]).upper() + s[1:]

class ModelPropertys():
    def __init__(self, type, name, context):
        name_str_strat = name.find('h') + len('h')
        name_str_end = name.find('[')
        if type == 'char':
            type = 'String'
        self.type = type
        self.name = small_str(name[name_str_strat:name_str_end])
        self.context = context