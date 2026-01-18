"""
直接测试采集API接口
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_collection_api():
    """测试采集API"""
    print("=" * 70)
    print("测试采集API接口")
    print("=" * 70)
    
    # 1. 登录获取token
    print("\n1. 登录获取token...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            data=login_data,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"   登录失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
        
        data = response.json()
        token = data.get("access_token")
        print(f"   登录成功，获取token: {token[:30] if token else 'None'}...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # 2. 获取采集源列表
        print("\n2. 获取采集源列表...")
        response = requests.get(
            f"{BASE_URL}/api/collection/sources",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            sources = response.json()
            print(f"   找到 {len(sources)} 个采集源")
            for source in sources:
                print(f"   - ID: {source.get('id')}, 名称: {source.get('name')}, 启用: {source.get('enabled')}")
            
            if sources:
                source_id = sources[0].get('id')
                
                # 3. 触发采集
                print(f"\n3. 触发采集 (Source ID: {source_id})...")
                response = requests.post(
                    f"{BASE_URL}/api/collection/sources/{source_id}/trigger",
                    headers=headers,
                    timeout=30  # 采集可能需要较长时间
                )
                
                print(f"   状态码: {response.status_code}")
                print(f"   响应头: {dict(response.headers)}")
                
                try:
                    result = response.json()
                    print(f"   响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                except:
                    print(f"   响应文本: {response.text[:500]}")
                
                if response.status_code == 200:
                    print("   [成功] 采集触发成功！")
                else:
                    print(f"   [失败] 采集触发失败: {response.status_code}")
            else:
                print("   没有采集源可供测试")
        else:
            print(f"   获取采集源失败: {response.status_code}")
            print(f"   响应: {response.text}")
    
    except Exception as e:
        print(f"   测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)

if __name__ == "__main__":
    test_collection_api()
