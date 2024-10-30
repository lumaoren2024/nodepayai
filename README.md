# nodepayai
nodepay.ai签到 100% 在线免费 Python3
通过我的RF注册：https://app.nodepay.ai/register?ref=PMLZWyjtnh4r9Ki
# 功能
服务器挂机使用，不用多ip切换。

打开链接并登录 ``https://app.nodepay.ai/dashboard``
在页面上按 F12 打开控制台并输入代码（Ctrl + Shift + i）检查
在控制台中输入 ``localStorage.getItem('np_token');``
"打印的文本是 NP_TOKEN"

# 运行代码的步骤 -
## 1、获取相关的代码
np_token 获取：chrome f12 进入开发中心，然后找到网络：device-networks 这样的标签。找到 authorization:里面的代码就可以了，千万别复制：Bearer

cookies 获取：chrome f12 进入开发中心，然后找到网络：device-networks 这样的标签。找到 cookie:里面的代码就可以了

## 2、安装组件
```bash
pip install -r requirements.txt
```

## 3、运行
```bash
python3 nodepay.py
```

一行一个号，一个号对应一个cookies..................



# 运行情况
出现下列log就代表在跑了
```bash
2024-07-30 04:37:18.263 | INFO     | __main__:ping:110 - Ping successful: {'success': True, 'code': 0, 'msg': 'Success', 'data': {'ip_score': 88}}
2024-07-30 04:37:48.621 | INFO     | __main__:ping:110 - Ping successful: {'success': True, 'code': 0, 'msg': 'Success', 'data': {'ip_score': 90}}
2024-07-30 04:38:18.968 | INFO     | __main__:ping:110 - Ping successful: {'success': True, 'code': 0, 'msg': 'Success', 'data': {'ip_score': 94}}
2024-07-30 04:38:59.338 | INFO     | __main__:ping:110 - Ping successful: {'success': True, 'code': 0, 'msg': 'Success', 'data': {'ip_score': 98}}
```
