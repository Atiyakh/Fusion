from Fluxon.Connect import ConnectionHandler, CloudStorageConnector

conn = ConnectionHandler('192.168.1.6', 8080)
cloud = CloudStorageConnector('192.168.1.6', 8888)

Item = "TREE"
file_path = r"C:\Users\skhodari\Desktop\New folder\VID_20231128_095751.mp4"
cloud_relative_path = r"AtiyaKh\dir1"

input("login...")
response = conn.send_request("login", {
    "username": "AtiyaKh",
    "password": "Atty@kh123",
    "email": "atiyaalkhodari1@gmail.com"
})
print(response)

if Item == "FILE":
    input("write file...")
    cloud_request = conn.send_request("write_file", {"path": cloud_relative_path})
    print(cloud_request)
    input("cloud interaction...")
    with open(file_path, 'rb') as file:
        cloud_response = cloud.send_request(cloud_request, conn.sessionid, payload=file.read())
elif Item == "DELETE":
    input("create folder...")
    cloud_request = conn.send_request("delete_item", {"path": cloud_relative_path})
    print(cloud_request)
    input("cloud interaction...")
    cloud_response = cloud.send_request(cloud_request, conn.sessionid)
elif Item == "READ":
    input("read file...")
    cloud_request = conn.send_request("read_file", {"path": cloud_relative_path})
    print(cloud_request)
    input("cloud interaction...")
    cloud_response = cloud.send_request(cloud_request, conn.sessionid)
    f = open(r"C:\Users\skhodari\Desktop\test__.mp4", 'wb')
    f.write(cloud_response); f.close()
elif Item == "TREE":
    input("read tree...")
    cloud_request = conn.send_request("read_tree", {"path": cloud_relative_path})
    print(cloud_request)
    input("cloud interaction...")
    cloud_response = cloud.send_request(cloud_request, conn.sessionid)
else:
    input("create folder...")
    cloud_request = conn.send_request("create_folder", {"path": cloud_relative_path})
    print(cloud_request)
    input("cloud interaction...")
    cloud_response = cloud.send_request(cloud_request, conn.sessionid)

print(cloud_response, 999)

r"""
input("login...")
response = conn.send_request("login", {
    "username": "AtiyaKh",
    "password": "lqwenfewf",
    "email": "atiyaalkhodari1@gmail.com",
})
print("signup response:", response)

input("create owner...")
cloud_request = conn.send_request("create_owner")
print("cloud request registered:", cloud_request)
input("make cloud request...")
cloud.send_request(cloud_request, conn.sessionid)
"""

r"""
input("login...")
response = conn.send_request('login', {
    'username': "AtiyaKh",
    "password": "lqwenfewf"
})

if response:
    print("logged in successfully...")
    input("create folder...")
    cloud_request = conn.send_request('write_file', {
        "path": "AtiyaKh/file.png"
    })
    if cloud_request not in ('failed', 'login required'):
        print("cloud request registered...", cloud_request)
        input("send cloud request...")
        with open(r"C:\Users\skhodari\Desktop\Fusion\Fusion\التقاط.PNG", 'rb') as file:
            cloud_response = cloud.send_request(cloud_request, conn.sessionid, payload=file.read())
        print("cloud response: ", cloud_response)
    else:
        print("Error", cloud_request)
"""
