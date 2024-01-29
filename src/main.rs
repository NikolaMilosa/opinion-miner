use clap::Parser;
use fetchers::Error;
use slog::{info, o, Drain, Logger};
use tokio_util::sync::CancellationToken;

use crate::fetchers::{dev_to_fetcher::DevToFetcher, Fetcher};

mod cli;
mod fetchers;

#[tokio::main]
async fn main() -> Result<(), Error> {
    let cli = cli::Cli::parse();
    let logger = get_logger(cli.log_level.clone());

    info!(logger, "Running fetchers...");
    let cancel_token = CancellationToken::new();

    let dev_to_fetcher = DevToFetcher::from_cli(&cli, cancel_token.clone())?;
    let dev_to_fetcher_logger = logger.clone();
    let dev_to_fetcher_handle =
        tokio::spawn(async move { dev_to_fetcher.run(dev_to_fetcher_logger).await });

    tokio::select! {
        _ = tokio::signal::ctrl_c() => {
            info!(logger, "Received shutdown request...");
            cancel_token.cancel()
        }
    }

    dev_to_fetcher_handle.await.unwrap();

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
