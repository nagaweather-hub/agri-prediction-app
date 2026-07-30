import requests

# --------------------------------------------------
# 1. 設定情報
# --------------------------------------------------
# マニュアル記載の正確なURL
AUTH_URL = "https://agrometeorology.jp/LBW_API/AuthenticationKey"

# 契約時のIDとパスワードを入力してください
USER_ID = "nagasaki-nougi-env"
PASSWORD = "TWnht4Xc"

# --------------------------------------------------
# 2. 認証キー取得関数
# --------------------------------------------------
def get_auth_key(url, userid, password):
    # マニュアルのパラメータ例に基づくJSONデータ
    payload = {
        "userid": userid,    # キー名は「userid」
        "password": password
    }
    
    # POSTメソッドで送信
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        # レスポンス形式が「文字列」のため、response.textで直接認証キーを取得
        auth_key = response.text.strip()
        print("認証キーの取得に成功しました！")
        print(f"取得した認証キー: {auth_key}")
        return auth_key
    else:
        print(f"認証エラー: ステータスコード {response.status_code}")
        print(response.text)
        return None

# --------------------------------------------------
# 実行処理
# --------------------------------------------------
if __name__ == "__main__":
    auth_key = get_auth_key(AUTH_URL, USER_ID, PASSWORD)