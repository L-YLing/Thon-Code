package: dict = {
    "ID": "thon-code-gui",
    "Name": "Thon Code",
    "Path": ".main.libs.langs_loader",
    "Entrance": "main.py"
}

import libs.langs_handle as langs_handle

langs_key = langs_handle.langs_handle()

class langs:
    _lang_data = langs_key.load_full_language()

for key, value in langs._lang_data.items():
    attr_name = key.replace(".", "_")
    setattr(langs, attr_name, value)