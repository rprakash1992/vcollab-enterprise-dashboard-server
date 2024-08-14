from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
from typing import List
from zipfile import ZipFile
import uuid
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import oci
from oci.object_storage import ObjectStorageClient
from oci.config import from_file, validate_config
import ast
import resend
from supabase import create_client, Client

load_dotenv()

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Data(BaseModel):
    fileName: str

class FileUrlData(BaseModel):
    fileUrl: str

class DeleteFileData(BaseModel):
    fileName: str

class FolderUrlData(BaseModel):
    folderUrl: str

class RegisterRequestMailData(BaseModel):
    name: str
    email: str

class SignUpData(BaseModel):
    email: str
    password: str

class RegisterNewUserData(BaseModel):
    name: str
    email: str
    password: str

class EmailVerifyData(BaseModel):
    name: str
    email: str
    userId: str

class RegisterConfirmationMainData(BaseModel):
    email: str
    type: str

class UserProfileData(BaseModel):
    name: str
    email: str

class InvitationEmailData(BaseModel):
    email: str
    itemName: str
    itemType: str

class InvitedItemsObject(BaseModel):
    itemId: int
    invitedBy: str
    role: int

class InvitedUsersData(BaseModel):
    email: str
    invitedItems: List[InvitedItemsObject]

class EmailData(BaseModel):
    email: str

oracle_bucket = os.getenv("ORACLE_BUCKET")
oracle_namespace = os.getenv("ORACLE_NAMESPACE")
# oracle_private_key = os.getenv("ORACLE_PRIVATE_KEY")
oracle_user_ocid = os.getenv("ORACLE_USER_OCID")
oracle_tenancy_ocid = os.getenv("ORACLE_TENANCY_OCID")
oracle_fingerprint = os.getenv("ORACLE_FINGERPRINT")
oracle_region = os.getenv("ORACLE_REGION")

supabase_url: str = os.getenv("SUPABASE_URL")
supabase_key: str = os.getenv("SUPABASE_KEY")
service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin = create_client(supabase_url, service_role_key)

resend.api_key = os.getenv("RESEND_ACCESS_KEY")

config = {
    "user": oracle_user_ocid,
    "key_content": """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAy9a+x9e+618NMzOlS6QXI3hl2Fu2ZRe/A0zRV/OajI9OlzjN
yRZZ5cgj6rkQCMycGC4OT+6wMiBwGQkEdvhHQ/DXKmAN2UKhhu6hxq7O2FpMXSrW
hUiPPZAahQUCmrCaXjg9bQnAfTihKpwmPAdZ22W/Pv67/EBlaWnsFbX8g6iYPaCK
NbRlF2nw6DR5XA0lVnvi4MIr/hx0omyxlsEHqVVHMNdip3Fo5vvKg/0mAkvtEfvL
aja2iKALlncuUkzNheKaP7Xnc4TSitn8SJmX1RT4B4rQBY6CxX9G9TVY2/3B8Sho
T+hun+zl46KMaHJY23hNYT3YGe6WATFWXJ3+jwIDAQABAoIBAAVT8p6km//o9x5c
fjiQ7G3n6rmSBB12Vm7OpjYnTuXXpRU8zdwwsl7YMWAkQDAKsRXMtmEOexqEUInG
+4/kg3BaLjWUVyhTnoc5W48m6I8tJQvWX88SC3RvfNH3RI8oiJBn5esgsyBSx5um
gzVUd9vNOAd8fwtj34K22w3iONx0Er10MIT4RoQBijX3IlCr+z1L2XSYEEKFlLXe
ymtyf01XIeWD/+9GpyxHhhsjx7/HiRcbIdsQ1cwsHbsAwIaWWHHlSVuEhDs+DgAG
g0YGrYfS3uDqPUXwY5Ryn5//gDatH4bFGp3Ferj5lQAs9mG1qMQKoitAjU6feYaF
EF69v3ECgYEA5fmuVe0fARlLuQ8DvGvD1DOabaYO0mTGMxPMMGwRZp9eepoxbPAt
JvS2ZUF/z5wLsPZll9N6KXBkG+NKvlakjhvgcoGxpgl2lemk1H77+nxq0MZ266h9
5u4MYOLP0rQd51HEFvE4JSJwtCMNTMr0fL2exsONY+ehZZbhAkrcpikCgYEA4ufl
9CXLHk8b8a7YhfjCrgy/3qvnFHe8SuefHb/+kt2pzKQdJmTVmdSTpbiRh3u6gCi0
ZSzTb81f95pLJOklLeSYAtvGbDES+5vmgKCGhFBinQya0CloQXOWwTckL00vemVQ
FcKA/Q5AkbuB4wIP8kd8PY3jx4+Wi22ptpU/5fcCgYBmbGEcm9LnJmD3NpyvWj+J
TsJEe2S2h3NOZE7Ycgj975SgffPtVLqHUw244wcNa645TkPI7sLFmey8DurHAsef
EwNPfDumeyh5c+mZSkTnNmpMOVfVdOE97F9O9zUf3mBDGcN/hEdBIqmXUNUnkmx4
8eq5E3bxO8RB/oSQBM9ooQKBgQC32ITs6KJGkHpnu+8bvY6fTx024bl9T/Z0Cm9V
v3YYsRkfAenMbe7TkPWAVKc1Sv61UEW5pDQ8Zf7Xs2AnK/A/2vN/fWqrxqdGze5Z
UbcsBaWg8dGNz771KR6AtpjO6o8JcIUO3GV+o8mVSoPW1pjtCRaVGR3xV1n25oeX
tB3tyQKBgQCG7s5B5Ou3BlkQI52KlL9I6Mn1E0sJ2QGkk7YRd1MGrUbq1A/sgKd9
11VMTHS+AezMcZ4EfdsdcOFBwqR8KnQEfonqZ3toQI5ECHb1k/vwe6CVCbcQCM1p
6Ah6jrg+DN6SkpcnBxwkXt2rR2LCYSWMXyo6ennSS5lhd/XIjnnsaQ==
-----END RSA PRIVATE KEY-----""",
    "fingerprint": oracle_fingerprint,
    "tenancy": oracle_tenancy_ocid,
    "region": oracle_region,
    "passphrase": None
}

validate_config(config)

object_storage = ObjectStorageClient(config)

@app.post("/upload-normal-file")
def upload_normal_file(file: UploadFile):
    fileObj = file.file
    file_name = file.filename
    file_extension_index = file_name.rindex(".")
    file_extension = file_name[file_extension_index:]
    unique_name = str(uuid.uuid1()) + file_extension
    content_type = file.content_type

    try: 
        object_storage.put_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=unique_name,
            put_object_body=fileObj,
            content_type=content_type
        )

        return {
            "success": True,
            "message": "File uploaded successfully",
            "data": [unique_name]
        }
    
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/upload-zip-file")
def upload_zip_file(file: UploadFile):
    fileObj = file.file
    unique_name = str(uuid.uuid1()) + ".zip"
    content_type = file.content_type

    try: 
        object_storage.put_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=unique_name,
            put_object_body=fileObj,
            content_type=content_type
        )

        response = object_storage.head_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=unique_name,
        )

        responseHeaders = response.headers
        size = int(responseHeaders['Content-Length'])

        eocd = fetch(unique_name, size - 22, 22)
        # start offset and size of the central directory
        cd_start = parse_int(eocd[16:20])
        cd_size = parse_int(eocd[12:16])

        cd = fetch(unique_name, cd_start, cd_size)

        zip = ZipFile(BytesIO(cd + eocd))

        file_names_list = []
        file_names_list.append(unique_name)

        for entry in zip.filelist:
            f_name = entry.filename

            # remove "/" from the end of filename
            if f_name[len(f_name) - 1] == "/":
                f_name = f_name[:len(f_name) - 1]
                file_names_list.append(f_name)
            # elif f_name.index("/")
            else:
                file_names_list.append(f_name)

        return {
            "success": True,
            "message": "File uploaded successfully",
            "data": file_names_list
        }
    
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/download-file")
def download_file(data: Data):
    filename = data.fileName

    try:
        object_storage.head_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=filename,
        )

    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }

    try:
        current_time = datetime.now()
        # Define the time delta for 15 minutes
        time_delta = timedelta(minutes=15)

        # Calculate the future time
        future_time = current_time + time_delta
        formatted_future_time = future_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        response = object_storage.create_preauthenticated_request(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            create_preauthenticated_request_details=oci.object_storage.models.CreatePreauthenticatedRequestDetails(
                name="EXAMPLE-name-Value",
                access_type="ObjectRead",
                time_expires=formatted_future_time,
                object_name=filename
            )
        )

        url = response.data.full_path

        return {
            "success": True,
            "message": "",
            "data": url
        }
    
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/delete-file")
def delete_file(data: DeleteFileData):
    file_name = data.fileName

    try: 
        response = object_storage.delete_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=file_name,
        )

        if response.status == 204:
            return {
                "success": True,
                "message": "File deleted successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong"
            }
    
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }

@app.post("/download-file-from-zip")
def download_file_from_zip(data: FileUrlData):
    file_url = data.fileUrl
    key = file_url.split("/")[0]

    try:
        payload = {
            "key": key + ".zip",
            "required_file": file_url
        }

        function_id = "ocid1.fnfunc.oc1.ap-hyderabad-1.aaaaaaaalgowlems5cg55cb5qjrikzmsg5kuzag25g5fseno5qynuypd445q"
        fn_mgmt_client = oci.functions.FunctionsManagementClient(config)
        fn_details = fn_mgmt_client.get_function(function_id=function_id).data
        fn_invoke = oci.functions.FunctionsInvokeClient(config)
        fn_invoke.base_client.set_region('ap-hyderabad-1')
        fn_invoke.base_client.endpoint = fn_details.invoke_endpoint

        response = fn_invoke.invoke_function(
            function_id=function_id,
            invoke_function_body=json.dumps(payload)
        )

        data = response.data.content

        response_str = data.decode('utf-8')

        # 2. Convert the string representation to a dictionary
        response_dict = ast.literal_eval(response_str)
        success = response_dict.get('success')
        url = response_dict.get('data')

        if success:
            return {
                "success": True,
                "message": "",
                "data": url
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong.",
            }
    
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/delete-file-from-zip")
def delete_file_from_zip(data: FileUrlData):
    file_url = data.fileUrl

    try: 
        response = object_storage.delete_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=file_url,
        )

        if response.status == 204:
            return {
                "success": True,
                "message": "File deleted successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong"
            }
    
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/download-folder-from-zip")
def download_folder_from_zip(data: FolderUrlData):
    folder_url = data.folderUrl
    key = folder_url.split("/")[0]

    try:
        payload = {
            "key": key + ".zip",
            "required_folder": folder_url
        }

        function_id = "ocid1.fnfunc.oc1.ap-hyderabad-1.aaaaaaaa6c3r5fqwknusewsazcm4khucwst5kvlmuvhgrmxgxuovxjfnaj2a"
        fn_mgmt_client = oci.functions.FunctionsManagementClient(config)
        fn_details = fn_mgmt_client.get_function(function_id=function_id).data
        fn_invoke = oci.functions.FunctionsInvokeClient(config)
        fn_invoke.base_client.set_region('ap-hyderabad-1')
        fn_invoke.base_client.endpoint = fn_details.invoke_endpoint

        response = fn_invoke.invoke_function(
            function_id=function_id,
            invoke_function_body=json.dumps(payload)
        )

        data = response.data.content

        response_str = data.decode('utf-8')

        # 2. Convert the string representation to a dictionary
        response_dict = ast.literal_eval(response_str)
        success = response_dict.get('success')
        url = response_dict.get('data')

        if success:
            return {
                "success": True,
                "message": "",
                "data": url
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong.",
            }
    
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/delete-folder-from-zip")
def delete_folder_from_zip(data: FolderUrlData):
    folder_url = data.folderUrl

    try:
        response = object_storage.delete_object(
            namespace_name=oracle_namespace,
            bucket_name=oracle_bucket,
            object_name=folder_url + ".zip",
        )

        if response.status == 204:
            return {
                "success": True,
                "message": "Folder deleted successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong"
            }
    
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/new-register-request-mail-to-admin")
def register_request_mail_to_admin(data: RegisterRequestMailData):
    name = data.name
    email = data.email
    
    try:
        params: resend.Emails.SendParams = {
            "from": "info@vcollab.ai",
            "to": ["ravi.prakash@vcollab.com"],
            "subject": "New Register Request: VCollab Dashboard App",
            "html": f"<p>A new register request has been received at VCollab Dashboard App from the below credentials:</p><br /><strong>Name: </strong> {name} <br /><strong>Email: </strong> {email}<br /><br /> Please visit the admin panel to approve or reject the user.<br /> <a href='https://dev.vcollab.ai/login' target='_blank'>dev.vcollab.ai<a/>",
        }
        
        response: resend.Email = resend.Emails.send(params)

        if response["id"]:
            return {
                "success": True,
                "message": "Email sent to admin successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong.",
            }

    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
  
@app.post("/register-confirmation-mail-to-user")
def register_confirmation_mail_to_user(data: RegisterConfirmationMainData):
    email = data.email
    type = data.type

    htmlText = "<p>Your request for registration at VCollab Dashboard App has been declined by the admin. Please contact admin for more details."

    if type == "approve":
        htmlText = "<div><p>Your request for registration at VCollab Dashboard App has been approved. You may login with your credentials now.</p><br /><a href='https://dev.vcollab.ai/login' target='_blank'>Click here to visit VCollab Dashboard</a><div>"


    params: resend.Emails.SendParams = {
        "from": "info@vcollab.ai",
        "to": [email],
        "subject": "Register Request: Vcollab Dashboard App",
        "html": htmlText,
    }

    try:
        response: resend.Email = resend.Emails.send(params)

        if response["id"]:
            return {
                "success": True,
                "message": "Email sent successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong.",
            }
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    

@app.post("/send-invitation-email")
def send_invitation_email(data: InvitationEmailData):
    email = data.email
    item_name = data.itemName
    item_type = data.itemType

    htmlText = f"<div><p>You have been invited to access a {item_type} '{item_name}' at VCollab Dashboard App.</p><br /><br /><a href='http://dev.vcollab.ai/register' target='_blank'>Please visit this link to register.</a></div>"

    params: resend.Emails.SendParams = {
        "from": "info@vcollab.ai",
        "to": [email],
        "subject": "Invitation: Vcollab Dashboard App",
        "html": htmlText,
    }

    try:
        response: resend.Email = resend.Emails.send(params)

        if response["id"]:
            return {
                "success": True,
                "message": "Email sent successfully.",
                "data": None
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong.",
            }
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/get-user-id-from-email")
def get_user_id_from_email(data: EmailData):
    email = data.email
    
    try:
        req_user = ""
        users_list = supabase_admin.auth.admin.list_users()

        for user in users_list:
            if user.email == email:
                req_user = user

        return {
            "success": True,
            "message": "",
            "data": req_user.id
        }
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }

def fetch(key_name, start, len):
    """
    range-fetches a S3 key
    """
    end = start + len - 1
    response = object_storage.get_object(
        namespace_name=oracle_namespace,
        bucket_name=oracle_bucket,
        object_name=key_name,
        range="bytes=%d-%d" % (start, end),
    )

    responseData = response.data
    return responseData.content

def parse_int(bytes):
    """
    parses 2 or 4 little-endian bits into their corresponding integer value
    """
    val = (bytes[0]) + ((bytes[1]) << 8)
    if len(bytes) > 3:
        val += ((bytes[2]) << 16) + ((bytes[3]) << 24)
    return val
