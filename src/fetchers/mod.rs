use slog::Logger;

use crate::cli::Cli;

pub mod dev_to_fetcher;

pub trait Fetcher: Sized {
    async fn run(&self, log: Logger) -> Result<(), Error>;

    fn from_cli(cli: &Cli) -> Result<Self, Error>;
}

#[derive(Debug)]
pub enum Error {
    Invalid(String),
    FailedScrape(String),
    Parse(String),
}
