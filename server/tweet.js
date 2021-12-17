//To create this database and collection, run "node db.js".
//If you want to use a different database or collection name,
//you are more than welcome to change it.
var MongoClient = require('mongodb').MongoClient;
var url = "mongodb://localhost:27017/";

MongoClient.connect(url, function(err, db) {
  if (err) throw err;
  //The database name 
  var dbo = db.db("twitterfeed");
  //Our Collection name
  dbo.createCollection("tweets", function(err, res) {
    if (err) throw err;
    console.log("Collection created!");
    db.close();
  });
}); 