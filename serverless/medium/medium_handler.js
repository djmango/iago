const https = require('https');

function getRequest(url) {
    return new Promise((resolve, reject) => {
        const req = https.get(url, res => {
            let rawData = '';

            res.on('data', chunk => {
                rawData += chunk;
            });

            res.on('end', () => {
                try {
                    resolve(JSON.parse(rawData.slice(16)));
                } catch (err) {
                    reject(new Error(err));
                }
            });
        });

        req.on('error', err => {
            reject(new Error(err));
        });
    });
}

exports.handler = async function (event, context, callback) {
    try {
        let url = event.pathParameters.url
        let id = url.split('/').pop().split('-').pop()
        let apiUrl = `https://medium.com/_/api/posts/${id}?format=json`
        let result = await getRequest(apiUrl);
        console.log('result is: ', result.payload);

        // response structure assume you use proxy integration with API gateway
        return JSON.stringify(result.payload);
    } catch (error) {
        console.log('Error is: ', error);
        return error.message
    }
};