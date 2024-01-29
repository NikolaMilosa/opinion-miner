use clap::Parser;
use fetchers::Error;
use slog::{info, o, Drain, Logger};

use crate::fetchers::{dev_to_fetcher::DevToFetcher, Fetcher};

mod cli;
mod fetchers;

#[tokio::main]
async fn main() -> Result<(), Error> {
    let cli = cli::Cli::parse();
    let logger = get_logger(cli.log_level.clone());

    info!(logger, "Running fetchers...");
    let fetcher = DevToFetcher::from_cli(&cli)?;
    fetcher.run(logger.clone()).await?;

    info!(logger, "Finished...");
    Ok(())
}

fn get_logger(level: String) -> Logger {
    let level = match level.to_lowercase().as_str() {
        "info" => slog::Level::Info,
        "warn" => slog::Level::Warning,
        "debug" => slog::Level::Debug,
        _ => panic!("Unsupported"),
    };

    let drain = slog_async::Async::new(
        slog::Fuse::new(slog::Filter::new(
            slog_term::FullFormat::new(slog_term::PlainSyncDecorator::new(std::io::stderr()))
                .build(),
            move |record: &slog::Record| record.level().is_at_least(level),
        ))
        .fuse(),
    )
    .build()
    .fuse();

    slog::Logger::root(drain, o!())
}
