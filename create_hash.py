# コマンドライン上で
# python create_hash.py 設定したいパスワード名
# ハッシュ化したものが返ってくる
from werkzeug.security import generate_password_hash
import sys

if len(sys.argv) < 2:
    print("使い方: python create_hash.py <パスワード>")
    sys.exit(1)

password_to_hash = sys.argv[1]

hashed_password = generate_password_hash(password_to_hash)

print(f"パスワード: {password_to_hash}")
print(f"生成されたハッシュ値: {hashed_password}")
