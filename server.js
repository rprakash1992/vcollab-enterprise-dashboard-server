const express = require("express");
const bodyParser = require("body-parser");
const cors = require('cors')
// require("dotenv").config();

const app = express();

const api = require("./routes");

// body-parser middleware
app.use(bodyParser.urlencoded({ limit: "100gb", extended: true }));
app.use(bodyParser.json({ limit: "100gb" }));

//cors
const corsOpts = {
  origin: '*',

  methods: [
    'GET',
    'POST',
    'PUT',
    "DELETE"
  ],

  allowedHeaders: [
    'Content-Type',
  ],
};

app.use(cors(corsOpts));
// app.use(cors())
// app.use(function (req, res, next) {
//   res.setHeader("Access-Control-Allow-Origin", "*");
//   res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE");
//   res.setHeader("Access-Control-Allow-Headers", "Content-Type");
//   res.setHeader("Access-Control-Allow-Credentials", true);
//   next();
// });

app.use("/", api);

const PORT = process.env.PORT || 8080;

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
