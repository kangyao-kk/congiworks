import sqlite3
conn = sqlite3.connect('oauth.db')
cursor = conn.cursor()

# 查看所有表名
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables:", cursor.fetchall())

# 查看 'clients' 表的所有数据
# 注意：把 'clients' 换成你刚才查到的表名
cursor.execute("SELECT * FROM oauth_clients;")
rows = cursor.fetchall()
print("oauth_clients 表的数据:", rows)

# 查看表结构
cursor.execute("PRAGMA table_info(oauth_clients);")
print("表结构:", cursor.fetchall())