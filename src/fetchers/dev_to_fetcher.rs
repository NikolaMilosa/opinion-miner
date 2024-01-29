use super::{Error, Fetcher};
use reqwest::{
    header::{HeaderMap, HeaderValue},
    Client, Url,
};
use serde::{Deserialize, Serialize};
use slog::{debug, Logger};
use tokio_util::sync::CancellationToken;

pub struct DevToFetcher {
    client: Client,
    base_url: Url,
    per_page: u128,
    token: CancellationToken,
}

impl Fetcher for DevToFetcher {
    async fn run(&self, log: Logger) {
        let url = self.base_url.join("articles").expect("can join url");
        let mut num_scrape: u128 = 1;
        loop {
            let request = self
                .client
                .get(url.clone())
                .query(&[
                    ("page", &num_scrape.to_string()),
                    ("per_page", &self.per_page.to_string()),
                ])
                .build()
                .expect("can build a request");

            debug!(log, "Full request: {:?}", request);

            let response = tokio::select! {
                _ = self.token.cancelled() => {
                    debug!(log, "Received shutdown");
                    break;
                }
                response = self
                .client
                .execute(request) => {
                    match response {
                        Ok(r) => r,
                        Err(e) => {
                            debug!(log, "Failed scrape with error: {:?}", e);
                            continue;
                        }
                    }
                }
            };

            num_scrape += 1;

            debug!(log, "Successfully scraped dev.to");

            let parsed = tokio::select! {
                _ = self.token.cancelled() => {
                    debug!(log, "Received shutdown");
                    break;
                },
                parsed = response.json::<Vec<ArticlePreFetch>>() => {
                    match parsed {
                        Ok(v) => v,
                        Err(e) => {
                            debug!(log, "Failed to decode with error: {:?}", e);
                            continue;
                        }
                    }
                }
            };

            for article in parsed {
                let content = match self.fetch_content(article.id, &log).await {
                    Ok(c) => c,
                    Err(Error::Shutdown) => break,
                    Err(e) => {
                        debug!(log, "Error while fetching article content: {:?}", e);
                        continue;
                    }
                };

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
        }
    }

    fn from_cli(cli: &crate::cli::Cli, token: CancellationToken) -> Result<Self, Error> {
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
            per_page: cli.dev_to_page,
            token,
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

        let response = tokio::select! {
            _ = self.token.cancelled() => {
                debug!(log, "Received shutdown");
                return Err(Error::Shutdown)
            },
            response = self.client.execute(request) => {
                match response {
                    Ok(v) => v,
                    Err(e) => return Err(Error::FailedScrape(e.to_string()))
                }
            }
        };

        tokio::select! {
            _ = self.token.cancelled() => {
                debug!(log, "Received shutdown");
                return Err(Error::Shutdown)
            }
            resp = response.json::<ArticleContent>() => {
                resp.map_err(|e| Error::Parse(e.to_string()))
            }
        }
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
