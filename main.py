from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
from io import BytesIO
from zipfile import ZipFile 
import uuid
import json
import os
import resend
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

class Data(BaseModel):
    fileName: str

class FileUrlData(BaseModel):
    fileUrl: str

class FolderUrlData(BaseModel):
    folderUrl: str

class RegisterRequestMailData(BaseModel):
    name: str
    email: str

class SignUpData(BaseModel):
    email: str
    password: str

class RegisterConfirmationMainData(BaseModel):
    email: str
    type: str

class UserProfileData(BaseModel):
    name: str
    email: str

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

my_access_key = os.getenv("MY_S3_ACCESS_KEY")
my_secret_key = os.getenv("MY_S3_SECRET_KEY")
my_s3_bucket = os.getenv("MY_S3_BUCKET")

s3_client = boto3.client(
    's3',
    aws_access_key_id = my_access_key,
    aws_secret_access_key = my_secret_key
)

lambda_client = boto3.client(
    'lambda',
    aws_access_key_id = my_access_key,
    aws_secret_access_key = my_secret_key,
    region_name="us-east-1"
)

supabase_url: str = os.getenv("SUPABASE_URL")
supabase_key: str = os.getenv("SUPABASE_KEY")
service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)
supabase_admin = create_client(supabase_url, service_role_key)

resend.api_key = os.getenv("RESEND_ACCESS_KEY")

@app.post("/upload-normal-file")
def upload_normal_file(file: UploadFile):
    fileObj = file.file
    file_name = file.filename
    file_extension_index = file_name.rindex(".")
    file_extension = file_name[file_extension_index:]
    unique_name = str(uuid.uuid1()) + file_extension

    try: 
        s3_client.upload_fileobj(fileObj, my_s3_bucket, unique_name)

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

    try: 
        s3_client.upload_fileobj(fileObj, my_s3_bucket, unique_name)

        response = s3_client.head_object(Bucket=my_s3_bucket, Key=unique_name)
        size = response['ContentLength']

        eocd = fetch(unique_name, size - 22, 22)

        # start offset and size of the central directory
        cd_start = parse_int(eocd[16:20])
        cd_size = parse_int(eocd[12:16])

        cd = fetch(unique_name, cd_start, cd_size)

        zip = ZipFile(BytesIO(cd + eocd))

        file_names_list = []
        file_names_list.append(unique_name)

        for entry in zip.filelist:
            file_names_list.append(entry.filename)

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
        s3_client.head_object(Bucket=my_s3_bucket, Key=filename)

    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }

    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={"Bucket": my_s3_bucket, "Key": filename},
            ExpiresIn=900
        )

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

@app.post("/download-file-from-zip")
def download_file_from_zip(data: FileUrlData):
    file_url = data.fileUrl
    key = file_url.split("/")[0]

    try:
        payload = {
            "file_key": key + ".zip",
            "required_file": file_url
        }

        response = lambda_client.invoke(
            FunctionName="downloadSingleFileFromZip",
            InvocationType='RequestResponse',  # Change this if needed
            # Payload=b'{file_key="17ca9168-26f2-11ef-be00-141333879bea.zip"}',  # Payload can be any JSON serializable object
            Payload=json.dumps(payload)
        )

        responsePayload = response["Payload"].read()
        responseBody = json.loads(responsePayload)["body"]
        url = json.loads(responseBody)["url"]

        return {
            "success": True,
            "message": "",
            "data": url
        }
    
    except Exception as e:
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/delete-file-from-zip")
def delete_file_from_zip(data: FileUrlData):
    fileUrl = data.fileUrl

    try: 
        s3_client.delete_object(Bucket=my_s3_bucket, Key=fileUrl)

        return {
            "success": True,
            "message": "File deleted successfully.",
            data: None
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
            "file_key": key + ".zip",
            "required_folder": folder_url
        }

        response = lambda_client.invoke(
            FunctionName="downloadFolderFromZip",
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        responsePayload = response["Payload"].read()
        responseBody = json.loads(responsePayload)["body"]
        url = json.loads(responseBody)["url"]

        return {
            "success": True,
            "message": "",
            "data": url
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
        s3_client.delete_object(Bucket=my_s3_bucket, Key=folder_url + ".zip")

        return {
            "success": True,
            "message": "Folder deleted successfully.",
            data: None
        }
    
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    
@app.post("/register-request-emails")
def register_request_main_to_admin(data: RegisterRequestMailData):
    name = data.name
    email = data.email

    params_to_admin: resend.Emails.SendParams = {
        "from": "info@vcollab.ai",
        "to": ["ravi.prakash@vcollab.com", "rprakash262@gmail.com"],
        "subject": "New Register Request: Vcollab Dashboard",
        "html": f"<p>A new register request has been received at VCollab Dashboard App from the below credentials:</p><br /><strong>Name: </strong> {name} <br /><strong>Email: </strong> {email}<br /><br /> Please visit the admin panel to approve or reject the user.",
    }

    params_to_user: resend.Emails.SendParams = {
        "from": "info@vcollab.ai",
        "to": email,
        "subject": "Register Request: Vcollab Dashboard",
        "html": f"<p>Thank you for registering at VCollab Dashboard App. You will be able to login once your request is approved by the admin.",
    }
    
    try:
        response_from_admin: resend.Email = resend.Emails.send(params_to_admin)
        response_from_user: resend.Email = resend.Emails.send(params_to_user)

        if response_from_admin["id"] and response_from_user["id"]:
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
    
@app.post("/sign-up-user")
def sign_up_user(data: SignUpData):
    email = data.email
    password = data.password

    try:
        response = supabase.auth.sign_up(
            credentials={
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": "https://dev.vcollab.ai/confirm-email"
                }
            }
        )

        if response.user.id:
            return {
                "success": True,
                "message": "User created successfully",
                "data": str(response.user.id)
            }
        else:
            return {
                "success": False,
                "errorMessage": "Something went wrong",
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
        htmlText = "<p>Your request for registration at VCollab Dashboard App has been approved. You may login with your credentials now."


    params: resend.Emails.SendParams = {
        "from": "info@vcollab.ai",
        "to": [email],
        "subject": "Register Request as Vcollab App",
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
    
@app.post("/create-user-profile")
def create_user_profile(data: UserProfileData):
    name = data.name
    email = data.email
    req_user = None

    try:
        users_list = supabase_admin.auth.admin.list_users()

        for user in users_list:
            if user.email == email:
                req_user = user

        response = (
            supabase.table("profiles")
            .insert({"id": req_user.id, "name": name, "email": email})
            .execute()
        )

        return {
            "success": True,
            "message": "Profile created successfully",
            "data": None
        }
    except Exception as e:
        print(e)
        return {
            "success": False,
            "errorMessage": str(e)
        }
    

def fetch(key_name, start, len):
    """
    range-fetches a S3 key
    """
    end = start + len - 1
    s3_object = s3_client.get_object(
        Bucket=my_s3_bucket,
        Key=key_name,
        Range="bytes=%d-%d" % (start, end),
        # ResponseContentEncoding='cp1252'
    )

    return s3_object['Body'].read()

def parse_int(bytes):
    """
    parses 2 or 4 little-endian bits into their corresponding integer value
    """
    val = (bytes[0]) + ((bytes[1]) << 8)
    if len(bytes) > 3:
        val += ((bytes[2]) << 16) + ((bytes[3]) << 24)
    return val
