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
from oci.config import validate_config
import ast
import resend
import base64
from keys import APP_NAME, APP_DOMAIN, ADMIN_DOMAIN, APP_EMAIL, ADMIN_EMAILS 

env = os.getenv("ENVIRONMENT")

if env == "development":
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

class RegisterConfirmationMailData(BaseModel):
    email: str
    name: str
    type: str

class InvitationEmailData(BaseModel):
    email: str
    itemName: str
    itemType: str

class EmailData(BaseModel):
    email: str

oracle_bucket = os.getenv("ORACLE_BUCKET")
oracle_namespace = os.getenv("ORACLE_NAMESPACE")
oracle_private_key_encoded = os.getenv("ORACLE_PRIVATE_KEY_ENCODED")
oracle_private_key = base64.b64decode(oracle_private_key_encoded)
oracle_user_ocid = os.getenv("ORACLE_USER_OCID")
oracle_tenancy_ocid = os.getenv("ORACLE_TENANCY_OCID")
oracle_fingerprint = os.getenv("ORACLE_FINGERPRINT")
oracle_region = os.getenv("ORACLE_REGION")

download_single_file_from_zip_function_id = os.getenv("DOWNLOAD_SINGLE_FILE_FROM_ZIP_FUNCTION_ID")
download_folder_from_zip_function_id = os.getenv("DOWNLOAD_FOLDER_FROM_ZIP_FUNCTION_ID")

app_name: str = APP_NAME
app_domain: str = APP_DOMAIN
admin_domain: str = ADMIN_DOMAIN
app_email: str = APP_EMAIL
admin_emails = ADMIN_EMAILS

resend.api_key = os.getenv("RESEND_ACCESS_KEY")

config = {
    "user": oracle_user_ocid,
    "key_content": oracle_private_key,
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

        # function_id = "ocid1.fnfunc.oc1.ap-hyderabad-1.aaaaaaaalgowlems5cg55cb5qjrikzmsg5kuzag25g5fseno5qynuypd445q"
        function_id = download_single_file_from_zip_function_id
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

        # function_id = "ocid1.fnfunc.oc1.ap-hyderabad-1.aaaaaaaa6c3r5fqwknusewsazcm4khucwst5kvlmuvhgrmxgxuovxjfnaj2a"
        function_id = download_folder_from_zip_function_id
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
    
@app.post("/send-emails-after-email-verification")
def register_request_mail_to_admin(data: RegisterRequestMailData):
    name = data.name
    email = data.email
    
    paramsToAdmin: resend.Emails.SendParams = {
        "from": app_email,
        # "to": ["ravi.prakash@vcollab.com", "mohan@vcollab.com", "srinivasamurthi@vcollab.com"],
        "to": admin_emails,
        "subject": f"{app_name}: New Registration Request",
        "html": f"""<div><p><b>Dear Administrator,</b></p>
<br />
<p>A new user has registered on <a href={app_domain} target='_blank'>{app_domain}</a>. Here are the details of the new user:</p>
<p><b>Name: {name}</b></p>
<p><b>Email: {email}</b></p>
<br />
<p>Kindly review the user’s profile and take any necessary administrative actions by visiting the admin panel.</p>
<p><a href={admin_domain} target='_blank'>Click here to visit Admin Panel</a></p></div>"""
    }
    
    paramsToUser: resend.Emails.SendParams = {
        "from": app_email,
        "to": [email],
        "subject": f"{app_name}: Email Successfully Verified!",
        "html": f"""<div><p><b>Dear {name},</b></p>
<br />
<p>Congratulations! Your email address has been successfully verified.</p>
<p>Your profile is currently reviewed by the admin. You can access your account once it is approved by the admin.</p>
<br />
<p>Best regards,</p>
<p>{app_name} Team</p><div>"""
    }
    
    try:
        responseFromAdmin: resend.Email = resend.Emails.send(paramsToAdmin)
        responseFromUser: resend.Email = resend.Emails.send(paramsToUser)

        if responseFromAdmin["id"] and responseFromUser["id"]:
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
  
@app.post("/register-confirmation-mail-to-user")
def register_confirmation_mail_to_user(data: RegisterConfirmationMailData):
    email = data.email
    name = data.name
    type = data.type

    htmlText = f"""<div><p><b>Dear {name},</b></p>
<br />
<p>Thank you for your interest in joining {app_name}.</p>
<p>After reviewing your registration, we regret to inform you that your account could not be approved at this time.</p> 
<p>Thank you for your understanding, and we appreciate your interest in {app_name}.</p>
<br />
<p>Best regards,</p>
<p>{app_name} Team</p>
<div>"""
    subject = f"{app_name}: Account Rejected!"
    
    if type == "approve":
        htmlText = f"""<div><p><b>Dear {name},</b></p>
<br />
<p>We are excited to inform you that your registration request on {app_name} has been successfully approved by the admin.</p>
<p>You may login with your credentials now by visiting the link below.</p>
<p><a href='{app_domain}/login' target='_blank'>Click here to Login</a></p>
<p>Welcome aboard, and enjoy your journey with us!</p>
<br />
<p>Best regards,</p>
<p>{app_name} Team</p>
<div>"""
        subject = f"{app_name}: Account Approved!"

    params: resend.Emails.SendParams = {
        "from": app_email,
        "to": [email],
        "subject": subject,
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

    htmlText = f"""<div><p><b>Dear {email},</b></p>
<br />
<p>You have been invited to access a {item_type}, <b>'{item_name}'</b> at {app_name}.</p>
<p>Please register at {app_name} to access the {item_type}.<p>
<p><a href='{app_domain}/register' target='_blank'>Please visit this link to register.</a></p>
<br />
<p>Best regards,</p>
<p>{app_name} Team</p>
</div>"""

    params: resend.Emails.SendParams = {
        "from": app_email,
        "to": [email],
        "subject": f"{app_name}: Invitation Received",
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
    
# @app.post("/get-user-id-from-email")
# def get_user_id_from_email(data: EmailData):
#     email = data.email
    
#     try:
#         req_user = ""
#         users_list = supabase_admin.auth.admin.list_users()

#         for user in users_list:
#             if user.email == email:
#                 req_user = user

#         return {
#             "success": True,
#             "message": "",
#             "data": req_user.id
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "errorMessage": str(e)
#         }

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
