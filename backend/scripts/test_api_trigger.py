"""
测试API触发采集接口
"""
import sys
import requests
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database import get_db, User
from app.utils.auth import create_access_token


def test_api_trigger():
    """测试API触发采集"""
    base_url = "http://localhost:8000"
    
    # 1. 登录获取token
    print("1. 登录获取token...")
    
    # 通过登录API获取token
    try:
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        response = requests.post(
            f"{base_url}/api/auth/login",
            data=login_data,  # 使用form data
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            print(f"   [成功] 登录成功，获取token: {token[:30] if token else 'None'}...")
        else:
            print(f"   [失败] 登录失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   [错误] 登录异常: {str(e)}")
        return
    
    # 2. 测试触发采集API
    print("\n2. 测试触发采集API...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/collection/sources/1/trigger",
            headers=headers,
            timeout=10
        )
        
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.text}")
        
        if response.status_code == 200:
            print("   [成功] API调用成功")
            result = response.json()
            print(f"   消息: {result.get('message', 'N/A')}")
        else:
            print(f"   [失败] API调用失败")
            try:
                error = response.json()
                print(f"   错误详情: {error.get('detail', 'N/A')}")
            except:
                print(f"   错误响应: {response.text}")
    
    except requests.exceptions.RequestException as e:
        print(f"   [错误] 请求异常: {str(e)}")
    
    # 3. 等待几秒后检查采集日志
    print("\n3. 等待5秒后检查采集日志...")
    import time
    time.sleep(5)
    
    try:
        response = requests.get(
            f"{base_url}/api/collection/logs?limit=3",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logs = response.json()
            print(f"   最近的采集日志数量: {len(logs)}")
            for log in logs[:3]:
                print(f"   - 状态: {log.get('status')}, URL: {log.get('url', 'N/A')[:50]}...")
        else:
            print(f"   [失败] 获取日志失败: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        print(f"   [错误] 请求异常: {str(e)}")


if __name__ == "__main__":
    test_api_trigger()
