use slog::Logger;
use tokio_util::sync::CancellationToken;

use crate::cli::Cli;

pub mod dev_to_fetcher;

pub trait Fetcher: Sized {
    async fn run(&self, log: Logger);

    fn from_cli(cli: &Cli, token: CancellationToken) -> Result<Self, Error>;
}

#[derive(Debug)]
pub enum Error {
    Invalid(String),
    FailedScrape(String),
    Parse(String),
    Shutdown,
}
