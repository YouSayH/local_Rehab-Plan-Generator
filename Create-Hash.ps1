#Requires -Version 5.1

[CmdletBinding()]
param (
    # Pythonスクリプトへのパス
    [Parameter(Mandatory=$false)]
    [string]$PythonScriptPath = ".\create_hash.py",

    # 仮想環境のアクティベートスクリプトへのパス
    [Parameter(Mandatory=$false)]
    [string]$VenvActivateScript = ".\venv_rehab\Scripts\Activate.ps1" # 仮想環境のパスは自分自身のものに変更してください。
)
# 仮想環境のアクティベートスクリプトが存在するか確認
if (Test-Path $VenvActivateScript) {
    # 既に有効化されているかに関わらず、念のため有効化を実行
    # ドットソース(. )で実行し、現在のPowerShellセッションに設定を適用する
    . $VenvActivateScript
    Write-Host "仮想環境を有効化しました。" -ForegroundColor Cyan
}
else {
    Write-Warning "仮想環境のアクティベートスクリプトが見つかりません。グローバルなPython環境で実行を試みます。"
}


# 1. Pythonスクリプトの存在を確認
if (-not (Test-Path $PythonScriptPath)) {
    Write-Error "エラー: Pythonスクリプト '$PythonScriptPath' が見つかりません。"
    return
}

# 2. 安全な資格情報ウィンドウを表示してパスワードを要求
try {
    $credential = Get-Credential -UserName "password" -Message "ハッシュ化したいパスワードを入力してください"
}
catch {
    Write-Warning "パスワードの入力をキャンセルしました。"
    return
}

# 3. 入力されたSecureStringを、Pythonに渡すための平文パスワードに変換
$securePassword = $credential.Password
$ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainTextPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
}
finally {
    # メモリ上の平文パスワードを即座に解放
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
}

# 4. Pythonスクリプトを実行し、平文パスワードを引数として渡す
Write-Host "--- Pythonスクリプトを実行します ---" -ForegroundColor Green
python.exe $PythonScriptPath $plainTextPassword
Write-Host "------------------------------------" -ForegroundColor Green

# 5. 使い終わった変数をクリア
Clear-Variable -Name credential, securePassword, ptr, plainTextPassword -ErrorAction SilentlyContinue