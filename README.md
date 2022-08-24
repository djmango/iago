<div id="top"></div>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->

<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
<!-- [![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url] -->

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/Jeeny-ai/iago">
    <img src="images/logo_square.jpg" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Iago</h3>

  <p align="center">
    An interface to Jeeny's Brain
    <br />
    <a href="https://github.com/Jeeny-ai/iago"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/Jeeny-ai/iago">View Demo</a>
    ·
    <a href="https://github.com/Jeeny-ai/iago/issues">Report Bug</a>
    ·
    <a href="https://github.com/Jeeny-ai/iago/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->
## About The Project

Iago is the interface to Jeeny's brain. The 'brain' does not currently represent any existing systems, rather an architercture. All the logic and code currently used for Jeeny's AI functionality is available in the repo. The main project is a Django API `/iago`, which hosts the REST API for the project, as well as primary logic for the brain. Currently, that includes language intellegence functionality, such as embedding, and similairty search, as well as content operations, such as scraping, updating, and searching. Additionally, the serverless framework is used for specific functions that require high-scalibity even for MVP phase. The config and code for those functions are located in `/serverless`. NGINX serves as a reverse proxy for the containerized Django Iago app. All elements of Iago are hosted on AWS, and automatically deployed there upon commit by GitHub Actions CI/CD.

<p align="right">(<a href="#top">back to top</a>)</p>

### Built With

* [Django](https://www.djangoproject.com/)
* [Docker](https://www.docker.com/)
* [Serverless](https://www.serverless.com/)
* [Nginx](https://www.nginx.com/)
* [SBERT](https://www.sbert.net/)
* [FAISS](https://github.com/facebookresearch/faiss)
* [Huggingface](https://huggingface.co/)
* [Scrapy](https://scrapy.org/)
* [Beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

This is an example of how you may give instructions on setting up your project locally.
To get a local copy up and running follow these simple example steps.

### Prerequisites

* docker & docker-compose

  ```sh
  brew install docker-compose
  ```

### Installation

1. Clone the repo

   ```sh
   git clone https://github.com/Jeeny-ai/iago.git
   ```

2. Create the `.env` file in the root directory of the project. See `example.env`

3. Build docker-compose cluster

   ```sh
   docker-compose build
   ```

4. Run docker-compose cluster

   ```sh
   docker-compose up
   ```

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

All requests to the API have examples in the Postman collection. Below is an example of the adjacent skills call using Curl.

``` sh
curl --location --request GET 'http://localhost:80/v0/skillspace/adjacent' \
--header 'Authorization: Basic YOUR_AUTH' \
--header 'Content-Type: application/json' \
--data-raw '{
    "skills": [
        "graphic design",
        "Node JS",
        "Photoshop",
        "PHP"
    ],
    "k": 4
}'
```

and the response will be:

```json
{
    "skills": [
        {
            "name": "Graphic Design",
            "original": "graphic design",
            "adjacent": [
                "Computer Graphics Design",
                "Design & Illustration",
                "Creative Design",
                "Computer Art"
            ]
        },
        {
            "name": "Node.js",
            "original": "Node JS",
            "adjacent": [
                "Express.js",
                "Npm",
                "Node Package Manager",
                "Socket.io"
            ]
        },
        {
            "name": "Photoshop",
            "original": "Photoshop",
            "adjacent": [
                "GIMP",
                "Adobe Lightroom",
                "Photo Editing",
                "Photoshop for Photographers"
            ]
        },
        {
            "name": "PHP",
            "original": "PHP",
            "adjacent": [
                "PHP Applications",
                "PhpBB",
                "PHPList",
                "PHPUnit"
            ]
        }
    ]
}
```

_For more examples, please refer to the [Documentation](https://example.com)_ which has to be generated #TODO

<p align="right">(<a href="#top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Jeeny-ai/iago.svg?style=for-the-badge
[contributors-url]: https://github.com/Jeeny-ai/iago/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Jeeny-ai/iago.svg?style=for-the-badge
[forks-url]: https://github.com/Jeeny-ai/iago/network/members
[stars-shield]: https://img.shields.io/github/stars/Jeeny-ai/iago.svg?style=for-the-badge
[stars-url]: https://github.com/Jeeny-ai/iago/stargazers
[issues-shield]: https://img.shields.io/github/issues/Jeeny-ai/iago.svg?style=for-the-badge
[issues-url]: https://github.com/Jeeny-ai/iago/issues
[license-shield]: https://img.shields.io/github/license/Jeeny-ai/iago.svg?style=for-the-badge
[license-url]: https://github.com/Jeeny-ai/iago/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png

![Alt text](/images/aladdin-iago.png?raw=true)
