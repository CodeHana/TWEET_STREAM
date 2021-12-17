const http = require('http')
const path = require('path')
const express = require('express')
const socketIo = require('socket.io')
const needle = require('needle')
const config = require('dotenv').config()
const TOKEN ='xxxx' 
const PORT = process.env.PORT || 3000

const app = express()
const server = http.createServer(app)
const io = socketIo(server)

// connect mongodb
const mongo = require('mongodb').MongoClient
const { Db } = require('mongodb')
const { assert } = require('console')

var mongoServer = mongo.connect('mongodb://127.0.0.1/ ', function(err, db){
    if(err){
        throw error;
    }
    console.log('MongoDB Connected...')
});

app.get('/', (req, res)=>{
    res.sendFile(path.resolve(__dirname, '../', 'client', 'index.html'))
})

const rulesURL = 'https://api.twitter.com/2/tweets/search/stream/rules'
const streamURL = 'https://api.twitter.com/2/tweets/search/stream?tweet.fields=public_metrics&expansions=author_id'

const rules= [{value : 'Tesla'},{value : 'TSLA'},{value : 'Elon Musk'} ]

// Get Stream Rules
async function getRules(){
    const response = await needle('get', rulesURL, {
        headers:{
            Authorization: `Bearer ${TOKEN}`,
        },
    })
    console.log(response.body)
    return response.body
}


// Set Stream Rules
async function setRules(){
    const data={
        add: rules
    }
    const response = await needle('post', rulesURL, data, {
        headers:{
            'content-type': 'application/json',
            Authorization: `Bearer ${TOKEN}`,
        },
    })
    return response.body
}

// Delete stream rules
async function deleteRules(rules) {
    if (!Array.isArray(rules.data)) {
      return null
    }
  
    const ids = rules.data.map((rule) => rule.id)
  
    const data = {
      delete: {
        ids: ids,
      },
    }
  
    const response = await needle('post', rulesURL, data, {
      headers: {
        'content-type': 'application/json',
        Authorization: `Bearer ${TOKEN}`,
      },
    })
  
    return response.body
  }

function streamTweets(socket ){
    const stream = needle.get(streamURL, {
        headers:{
            Authorization: `Bearer ${TOKEN}`
        }   
    })
    
    stream.on('data', (data)=>{
        try {
            const json = JSON.parse(data)
            // console.log(json)
            socket.emit('tweet', json)           
        } catch (error){}
    });
}

// Get Stream Rules
async function connectToMongoDB(){
    await mongo().then((mongoose)=> {
        try{
            console.log('Connected to mongodb!')
        }finally {
            mongoose.connect.close()
        }
    })
}


io.on('connection', async ()=>{
    console.log('Client connected...')

    let currentRules

    try{
        //Get all stream rules
        currentRules = await getRules()

        //Delete all stream rules
        await deleteRules(currentRules)

        //set rules based on array above
        await setRules()
        
    } catch (error){
        console.error(error)
        process.exit(1)
    }

    streamTweets(io)
    
})

// (async() =>{
//     let currentRules

//     try{
//         //Get all stream rules
//         currentRules = await getRules()

//         //Delete all stream rules
//         await deleteRules(currentRules)

//         //set rules based on array above
//         await setRules()
        
//     } catch (error){
//         console.error(error)
//         process.exit(1)
//     }

//     streamTweets()
// })()

server.listen(PORT, () => console.log(`Listening on port ${PORT}`))