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
        console.log(event)
        if ('body' in event && 'url' in event.body) {
            let url = JSON.parse(event.body).url;
        } else if ('pathParameters' in event && 'url' in event.pathParameters) {
            let url = event.pathParameters.url;
        } else if ('url' in event) {
            let url = event.url;
        } else {
            throw new Error('Invalid request. Must contain URL in body or pathParameters.');
        }
        // TODO: should put a validator here to ensure its a medium url or at least has a medium id
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