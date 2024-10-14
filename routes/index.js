const express = require("express");
const multer = require("multer");
const objectstorage = require("oci-objectstorage");
const common = require("oci-common");
// const unzipper = require("unzipper");
// const path = require("path");
// const fs = require("fs");
// const stream = require("stream");
const uuid = require("uuid");
const AdmZip = require("adm-zip");
const fs = require('fs');
const path = require('path');
const StreamZip = require('node-stream-zip');
// const fn = require("oci-functions");
// const helper = require("oci-common/lib/helper");
// var encoding = require("encoding-japanese");
// const { pipeline, Readable } = require("stream");
const { Resend } = require("resend");

const {
  resendAccessKey,
  appName,
  appDomain,
  adminDomain,
  appEmail,
  adminEmails,
  oracleNamespace,
  oracleBucket,
  oracleUserOcid,
  oracleTenancyOcid,
  oracleFingerprint,
  oracleRegion,
  oraclePrivateKeyEncoded,
} = require("../config/keys");

// const storage = multer.memoryStorage();
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/'); // Specify the directory to store files temporarily
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  },
});

let oraclePrivateKeyEncodedBuffer = Buffer.from(oraclePrivateKeyEncoded, "base64");
// Encode the Buffer as a utf8 string
let oraclePrivateKey = oraclePrivateKeyEncodedBuffer.toString("utf-8");

// const provider = new common.ConfigFileAuthenticationDetailsProvider();
const region = common.Region.register("ap-hyderabad-1",  common.Realm.OC1, "hyd")
const provider = new common.SimpleAuthenticationDetailsProvider(
  oracleTenancyOcid,
  oracleUserOcid,
  oracleFingerprint,
  oraclePrivateKey,
  null,
  region,
);

const upload = multer({
  storage,
  limits: {
    fileSize: 100 * 1024 * 1024 * 1024, // 100 GB
  },
});

// Create uploads directory if it doesn't exist
if (!fs.existsSync('uploads')) {
  fs.mkdirSync('uploads');
}

const router = express.Router();
const resend = new Resend(resendAccessKey);
const client = new objectstorage.ObjectStorageClient({
  authenticationDetailsProvider: provider,
});

// const generateStreamFromString = (data) => {
//   let Readable = require("stream").Readable;
//   let stream = new Readable();
//   stream.push(data); // the string you want
//   stream.push(null);
//   return stream;
// };

router.post("/upload-normal-file", upload.single("file"), async (req, res) => {
  const { file } = req;

  const tempFilePath = file?.path;
  const fileName = file?.originalname;
  const fileExtensionIndex = fileName?.lastIndexOf(".");
  const fileExtension = fileName?.slice(fileExtensionIndex);
  const uniqueName = String(uuid.v4() + fileExtension);

  // Read the file from the temporary location
  const fileStream = fs.createReadStream(tempFilePath);

  const putObjectRequest = {
    namespaceName: oracleNamespace,
    bucketName: oracleBucket,
    objectName: uniqueName,
    contentLength: file?.size,
    putObjectBody: fileStream,
    contentType: file?.mimetype,
  };

  try {
    await client.putObject(putObjectRequest);

    fs.unlinkSync(tempFilePath);

    res.json({
      success: true,
      message: "File uploaded successfully",
      data: [uniqueName],
    });
  } catch (err) {
    console.log(err)
    res.json({
      success: false,
      errorMessage: String(err),
    });
  }
});

router.post("/upload-zip-file", upload.single("file"), async (req, res) => {
  try {
    const { file } = req;
    uniqueName = String(uuid.v4()) + ".zip";

    const tempFilePath = file?.path;
    const fileStream = fs.createReadStream(tempFilePath);

    const putObjectRequest = {
      namespaceName: oracleNamespace,
      bucketName: oracleBucket,
      objectName: uniqueName,
      contentLength: file.size,
      putObjectBody: fileStream,
      contentType: file.mimetype,
    };

    await client.putObject(putObjectRequest);

    const fileNamesList = [uniqueName];
    const zip = new StreamZip({
      file: tempFilePath,
      storeEntries: true
    });
  
    zip.on('ready', () => {
      // Take a look at the files
      console.log('Entries read: ' + zip.entriesCount);
      for (const entry of Object.values(zip.entries())) {
          // const desc = entry.isDirectory ? 'directory' : `${entry.size} bytes`;
          // console.log(`Entry ${entry.name}: ${desc}`);
          fileNamesList.push(entry?.name);
      }

  
      // Read a file in memory
      // let zipDotTxtContents = zip.entryDataSync('path/inside/zip.txt').toString('utf8');
      // console.log("The content of path/inside/zip.txt is: " + zipDotTxtContents);
  
      // Do not forget to close the file once you're done
      zip.close()
      fs.unlinkSync(tempFilePath);
      res.json({
        success: true,
        message: "File uploaded successfully",
        data: fileNamesList,
      });
    });
  } catch (err) {
    return {
      success: false,
      errorMessage: String(err),
    };
  }
});

// router.post("/upload-zip-file", upload.single("file"), async (req, res) => {
//   try {
//     const { file } = req;
//     uniqueName = String(uuid.v4()) + ".zip";

//     const tempFilePath = file?.path;
//     const fileStream = fs.createReadStream(tempFilePath);

//     const putObjectRequest = {
//       namespaceName: oracleNamespace,
//       bucketName: oracleBucket,
//       objectName: uniqueName,
//       contentLength: file.size,
//       putObjectBody: fileStream,
//       contentType: file.mimetype,
//     };

//     await client.putObject(putObjectRequest);

//     const fileNamesList = [uniqueName];
//     const zipFile = new AdmZip(tempFilePath);
//     const entries = zipFile.getEntries();

//     entries.forEach((entry) => {
//       fileNamesList.push(entry?.entryName);
//     });

//     fs.unlinkSync(tempFilePath);

//     res.json({
//       success: true,
//       message: "File uploaded successfully",
//       data: fileNamesList,
//     });
//   } catch (err) {
//     return {
//       success: false,
//       errorMessage: String(err),
//     };
//   }
// });

// router.post("/upload-normal-file", upload.single("file"), async (req, res) => {
//   const { file } = req;
//   const fileName = file?.originalname;
//   const fileExtensionIndex = fileName?.lastIndexOf(".");
//   const fileExtension = fileName?.slice(fileExtensionIndex);
//   const uniqueName = String(uuid.v4() + fileExtension);

//   const putObjectRequest = {
//     namespaceName: oracleNamespace,
//     bucketName: oracleBucket,
//     objectName: uniqueName,
//     contentLength: file?.size,
//     putObjectBody: generateStreamFromString(file?.buffer),
//     contentType: file?.mimetype,
//   };

//   try {
//     await client.putObject(putObjectRequest);

//     res.json({
//       success: true,
//       message: "File uploaded successfully",
//       data: [uniqueName],
//     });
//   } catch (err) {
//     res.json({
//       success: false,
//       errorMessage: String(err),
//     });
//   }
// });

// router.post("/upload-zip-file", upload.single("file"), async (req, res) => {
//   try {
//     const { file } = req;
//     uniqueName = String(uuid.v4()) + ".zip";

//     const putObjectRequest = {
//       namespaceName: oracleNamespace,
//       bucketName: oracleBucket,
//       objectName: uniqueName,
//       contentLength: file.size,
//       putObjectBody: generateStreamFromString(file.buffer),
//       contentType: file.mimetype,
//     };

//     await client.putObject(putObjectRequest);

//     const fileNamesList = [uniqueName];
//     const zipFile = new AdmZip(file?.buffer);
//     const entries = zipFile.getEntries();

//     entries.forEach((entry) => {
//       fileNamesList.push(entry?.entryName);
//     });

//     res.json({
//       success: true,
//       message: "File uploaded successfully",
//       data: fileNamesList,
//     });
//   } catch (err) {
//     return {
//       success: false,
//       errorMessage: String(err),
//     };
//   }
// });

router.post("/download-file", async (req, res) => {
  try {
    const { fileName } = req.body;

    const createPreauthenticatedRequestDetails = {
      name: "EXAMPLE-name-Value",
      objectName: fileName,
      accessType:
        objectstorage.models.CreatePreauthenticatedRequestDetails.AccessType
          .ObjectRead,
      timeExpires: new Date(new Date()?.getTime() + 15 * 60000),
    };

    const createPreauthenticatedRequestRequest = {
      namespaceName: oracleNamespace,
      bucketName: oracleBucket,
      createPreauthenticatedRequestDetails:
        createPreauthenticatedRequestDetails,
    };

    const createPreauthenticatedRequestResponse =
      await client.createPreauthenticatedRequest(
        createPreauthenticatedRequestRequest
      );

    const downloadUrl =
      createPreauthenticatedRequestResponse?.preauthenticatedRequest?.fullPath;

    res.json({
      success: true,
      message: "",
      data: downloadUrl,
    });
  } catch (err) {
    res.json({
      success: false,
      errorMessage: String(err),
    });
  }
});

router.post("/download-file-from-zip", async (req, res) => {
  try {
    const { fileUrl } = req.body;

    const indexOfFirstSlash = fileUrl?.indexOf("/");
    const key = fileUrl?.slice(0, indexOfFirstSlash);
    const zipFileName = key + ".zip";
    const requiredfileName = fileUrl?.slice(indexOfFirstSlash + 1);

    if (!zipFileName || !requiredfileName) {
      return res.status(400).json({
        success: false,
        errorMessage: "Missing zip file or specific file parameters",
      });
    }

    const getObjectResponse = await client.getObject({
      namespaceName: oracleNamespace,
      bucketName: oracleBucket,
      objectName: zipFileName,
    });

    // console.log("Object downloaded:", getObjectResponse);

    // Step 2: Check if the response has a valid body
    if (!getObjectResponse || !getObjectResponse.value) {
      return res.status(500).send("Failed to download the ZIP file.");
    }

    // Step 3: Convert the response body to a buffer (if needed)
    const chunks = [];
    for await (let chunk of getObjectResponse.value) {
      chunks.push(chunk);
    }
    const zipBuffer = Buffer.concat(chunks);

    // console.log("ZIP buffer length:", zipBuffer.length);

    // Step 4: Extract the specific file using `adm-zip`
    const zip = new AdmZip(zipBuffer);
    const zipEntries = zip.getEntries();

    const fileEntry = zipEntries.find(
      (entry) => entry.entryName === requiredfileName
    );

    if (!fileEntry) {
      return res.status(404).json({
        success: false,
        errorMessage: "File not found inside the ZIP",
      });
    }

    // Step 5: Send the file content to the client
    res.setHeader(
      "Content-Disposition",
      `attachment; filename="${fileEntry.name}"`
    );
    res.setHeader("Content-Type", "application/octet-stream");

    return res.send(fileEntry.getData());
  } catch (error) {
    console.error("Error downloading the ZIP file:", error);
    res.status(500).json({ success: false, errorMessage: error });
  }
});

router.post("/download-file-from-zip2", async (req, res) => {
  const { fileUrl } = req.body;
  key = fileUrl?.split("/")[0];
  console.log(fileUrl);
  console.log(key);
  payload = {
    key: key + ".zip",
    requiredFile: fileUrl,
  };

  console.log(payload);

  const request = {
    functionId:
      "ocid1.fnfunc.oc1.ap-hyderabad-1.aaaaaaaapoizyhcu7y6bfhwpm7y4runfes3jn2d3nshbzixju7dvzs7gmr7q",
    invokeFunctionBody: JSON.stringify(payload),
  };

  try {
    const response = await fnClient.invokeFunction(request);
    console.log(response);
    // console.log(response.value)
    const chunks = [];
    const stream = response?.value;

    for await (const chunk of stream) {
      chunks.push(Buffer.from(chunk));
    }

    const data = Buffer.concat(chunks).toString("utf-8");

    console.log(data);

    res.json({
      success: true,
      message: "",
      data: JSON.parse(data),
    });
  } catch (err) {
    console.log(err);
    res.json({
      success: false,
      errorMessage: String(err),
    });
  }
});

router.post("/delete-file", async (req, res) => {
  try {
    const { fileName } = req.body;

    const deleteObjectRequest = {
      namespaceName: oracleNamespace,
      bucketName: oracleBucket,
      objectName: fileName,
    };

    await client?.deleteObject(deleteObjectRequest);

    res.json({
      success: true,
      message: "File deleted successfully.",
      data: null,
    });
  } catch (error) {
    res.json({
      success: false,
      errorMessage: String(error),
    });
  }
});

router.post("/send-emails-after-email-verification", async (req, res) => {
  try {
    const { name, email } = req?.body;

    paramsToAdmin = {
      from: appEmail,
      // "to": ["ravi.prakash@vcollab.com", "mohan@vcollab.com", "srinivasamurthi@vcollab.com"],
      to: adminEmails,
      subject: `$${appName}: New Registration Request`,
      html: `<div><p><b>Dear Administrator,</b></p>
<br />
<p>A new user has registered on <a href=${appDomain} target='_blank'>${appDomain}</a>. Here are the details of the new user:</p>
<p><b>Name: ${name}</b></p>
<p><b>Email: ${email}</b></p>
<br />
<p>Kindly review the user’s profile and take any necessary administrative actions by visiting the admin panel.</p>
<p><a href=${adminDomain} target='_blank'>Click here to visit Admin Panel</a></p></div>`,
    };

    paramsToUser = {
      from: appEmail,
      to: [email],
      subject: `${appName}: Email Successfully Verified!`,
      html: `<div><p><b>Dear ${name},</b></p>
<br />
<p>Congratulations! Your email address has been successfully verified.</p>
<p>Your profile is currently reviewed by the admin. You can access your account once it is approved by the admin.</p>
<br />
<p>Best regards,</p>
<p>${appName} Team</p><div>`,
    };

    const [adminResponse, userResponse] = await Promise.allSettled([
      resend.emails.send(paramsToAdmin),
      resend.emails.send(paramsToUser),
    ]);

    if (
      adminResponse?.status === "fulfilled" &&
      userResponse?.status === "fulfilled"
    ) {
      res.json({
        success: true,
        message: "Email sent successfully.",
        data: null,
      });
    } else {
      res.json({
        success: false,
        errorMessage: "Something went wrong.",
      });
    }
  } catch (error) {
    console.log(error);
    res.json({
      success: false,
      errorMessage: JSON.stringify(error),
    });
  }
});

router.post("/register-confirmation-mail-to-user", async (req, res) => {
  try {
    const { email, name, type } = req?.body;

    let htmlText = `<div><p><b>Dear ${name},</b></p>
<br />
<p>Thank you for your interest in joining ${appName}.</p>
<p>After reviewing your registration, we regret to inform you that your account could not be approved at this time.</p> 
<p>Thank you for your understanding, and we appreciate your interest in ${appName}.</p>
<br />
<p>Best regards,</p>
<p>${appName} Team</p>
<div>`;

    let subject = `${appName}: Account Rejected!`;

    if (type == "approve") {
      htmlText = `<div><p><b>Dear ${name},</b></p>
<br />
<p>We are excited to inform you that your registration request on ${appName} has been successfully approved by the admin.</p>
<p>You may login with your credentials now by visiting the link below.</p>
<p><a href='${appDomain}/login' target='_blank'>Click here to Login</a></p>
<p>Welcome aboard, and enjoy your journey with us!</p>
<br />
<p>Best regards,</p>
<p>${appName} Team</p>
<div>`;

      subject = `${appName}: Account Approved!`;
    }

    const params = {
      from: appEmail,
      to: [email],
      subject: subject,
      html: htmlText,
    };

    const { error } = await resend.emails.send(params);

    if (error) {
      res.json({
        success: false,
        errorMessage: "Something went wrong.",
      });
    }

    res.json({
      success: true,
      message: "Email sent successfully.",
      data: null,
    });
  } catch (error) {
    console.log(error);
    res.json({
      success: false,
      errorMessage: JSON.stringify(error),
    });
  }
});

router.post("/send-invitation-email", async (req, res) => {
  try {
    const { email, itemName, itemType } = req?.body;

    const htmlText = `<div><p><b>Dear ${email},</b></p>
<br />
<p>You have been invited to access a ${itemType}, <b>'${itemName}'</b> at ${appName}.</p>
<p>Please register at ${appName} to access the ${itemType}.<p>
<p><a href='${appDomain}/register' target='_blank'>Please visit this link to register.</a></p>
<br />
<p>Best regards,</p>
<p>${appName} Team</p>
</div>`;

    const params = {
      from: appEmail,
      to: [email],
      subject: `${appName}: Invitation Received`,
      html: htmlText,
    };

    const { error } = await resend.emails.send(params);

    if (error) {
      res.json({
        success: false,
        errorMessage: "Something went wrong.",
      });
    }

    res.json({
      success: true,
      message: "Email sent successfully.",
      data: null,
    });
  } catch (error) {
    console.log(error);
    res.json({
      success: false,
      errorMessage: JSON.stringify(error),
    });
  }
});

module.exports = router;
