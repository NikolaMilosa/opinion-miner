use super::{Error, Fetcher};
use reqwest::{
    header::{HeaderMap, HeaderValue},
    Client, Url,
};
use serde::{Deserialize, Serialize};
use slog::{debug, Logger};

pub struct DevToFetcher {
    client: Client,
    base_url: Url,
}

impl Fetcher for DevToFetcher {
    async fn run(&self, log: Logger) -> Result<(), Error> {
        let url = self.base_url.join("articles").expect("can join url");
        let request = self
            .client
            .get(url)
            .query(&[("page", "1"), ("per_page", "10")])
            .build()
            .expect("can build a request");

        debug!(log, "Full request: {:?}", request);

        let response = self
            .client
            .execute(request)
            .await
            .map_err(|e| Error::FailedScrape(e.to_string()))?;

        debug!(log, "Successfully scraped dev.to");

        let parsed = response
            .json::<Vec<ArticlePreFetch>>()
            .await
            .map_err(|e| Error::Parse(e.to_string()))?;

        for article in parsed {
            let content = self.fetch_content(article.id, &log).await?;

            let full_article = Article {
                body_html: content.body_html,
                description: article.description,
                id: article.id,
                title: article.title,
            };
            println!(
                "{}",
                serde_json::to_string(&full_article).expect("can serialize into json")
            )
        }

        Ok(())
    }

    fn from_cli(cli: &crate::cli::Cli) -> Result<Self, Error> {
        let mut headers = HeaderMap::new();
        headers.append(
            "accept",
            HeaderValue::from_str("application/vnd.forem.api-v1+json")
                .expect("can create header value"),
        );
        headers.append(
            "user-agent",
            HeaderValue::from_str("rust-code").expect("can create header value"),
        );
        Ok(Self {
            client: reqwest::Client::builder()
                .default_headers(headers)
                .build()
                .map_err(|e| Error::Invalid(e.to_string()))?,
            base_url: cli.dev_to_url.clone(),
        })
    }
}

impl DevToFetcher {
    async fn fetch_content(&self, id: u128, log: &Logger) -> Result<ArticleContent, Error> {
        let url = self
            .base_url
            .join("articles/")
            .expect("can join url")
            .join(&id.to_string())
            .expect("can join url");

        let request = self.client.get(url).build().expect("can build request");

        debug!(
            log,
            "Requesting article with id {} with payload: {:?}", id, request
        );

        let response = self
            .client
            .execute(request)
            .await
            .map_err(|e| Error::FailedScrape(e.to_string()))?;

        response
            .json::<ArticleContent>()
            .await
            .map_err(|e| Error::Parse(e.to_string()))
    }
}

#[derive(Deserialize, Serialize)]
struct ArticlePreFetch {
    id: u128,
    title: String,
    description: String,
}

#[derive(Deserialize, Serialize)]
struct ArticleContent {
    body_html: String,
}

#[derive(Serialize)]
struct Article {
    id: u128,
    title: String,
    description: String,
    body_html: String,
}
