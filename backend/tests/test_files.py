"""
文件管理API测试
"""
import pytest
from fastapi import status
from pathlib import Path
import tempfile
import os


def test_list_files_empty(client, auth_headers):
    """测试空文件列表"""
    response = client.get("/api/files/", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0


def test_upload_file(client, auth_headers, db_session, tmp_path):
    """测试文件上传"""
    # 设置临时上传目录
    from app.storage import FileManager
    FileManager.uploads_dir = tmp_path / "uploads"
    FileManager.uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试文件内容
    file_content = "# Test File\n\nThis is a test markdown file."
    
    response = client.post(
        "/api/files/upload",
        headers=auth_headers,
        files={"file": ("test.md", file_content, "text/markdown")},
        data={"title": "Test File"}
    )
    
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == "Test File"
    assert data["file_type"] == "upload"


def test_get_file_not_found(client, auth_headers):
    """测试获取不存在的文件"""
    response = client.get("/api/files/999", headers=auth_headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_delete_file(client, auth_headers, db_session, tmp_path):
    """测试删除文件"""
    from app.storage import FileManager
    from app.database import File, User
    
    # 设置临时目录
    FileManager.uploads_dir = tmp_path / "uploads"
    FileManager.uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建测试用户和文件
    user = db_session.query(User).filter(User.username == "testuser").first()
    
    # 创建文件记录
    file_record = File(
        title="Test Delete",
        upload_user_id=user.id,
        file_path="uploads/test/delete.md",
        file_hash="testhash"
    )
    db_session.add(file_record)
    db_session.commit()
    
    # 创建物理文件
    file_path = FileManager.uploads_dir / "test" / "delete.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("# Test")
    
    # 删除文件
    response = client.delete(f"/api/files/{file_record.id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    
    # 验证文件已删除
    deleted_file = db_session.query(File).filter(File.id == file_record.id).first()
    assert deleted_file is None


def test_list_files_pagination(client, auth_headers, db_session):
    """测试文件列表分页"""
    from app.database import File, User
    
    user = db_session.query(User).filter(User.username == "testuser").first()
    
    # 创建多个文件
    for i in range(25):
        file_record = File(
            title=f"Test File {i}",
            upload_user_id=user.id,
            file_path=f"uploads/test/file_{i}.md",
            file_hash=f"hash_{i}"
        )
        db_session.add(file_record)
    db_session.commit()
    
    # 测试第一页
    response = client.get("/api/files/?page=1&page_size=10", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 25
    assert len(data["items"]) == 10
    assert data["page"] == 1


def test_search_files(client, auth_headers, db_session):
    """测试文件搜索"""
    from app.database import File, User
    
    user = db_session.query(User).filter(User.username == "testuser").first()
    
    # 创建测试文件
    file1 = File(
        title="Python Tutorial",
        upload_user_id=user.id,
        file_path="uploads/test/python.md",
        file_hash="hash1"
    )
    file2 = File(
        title="JavaScript Guide",
        upload_user_id=user.id,
        file_path="uploads/test/js.md",
        file_hash="hash2"
    )
    db_session.add_all([file1, file2])
    db_session.commit()
    
    # 搜索Python
    response = client.get("/api/files/?search=Python", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Python Tutorial"
