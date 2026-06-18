# import base64
# import requests
# import json
# # 配置
# api_url = 'http://127.0.0.1:5000/users'

# response = requests.post(api_url, json={
#     "name": "percy",
#     "email": "ykkillian@gmail.com",
#     "age": 123
# })
# data = response.json()
# formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
# print(formatted_json)



# import base64
# import requests
# import json
# # 配置
# api_url = 'http://127.0.0.1:5000/users/1'

# response = requests.delete(api_url, )
# data = response.json()
# formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
# print(formatted_json)

import base64
import requests
import json
# 配置
api_url = 'http://127.0.0.1:5000/users/2'

response = requests.get(api_url)
data = response.json()
formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
print(formatted_json)
