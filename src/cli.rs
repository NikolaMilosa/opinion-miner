use clap::Parser;
use reqwest::Url;

#[derive(Parser, Debug)]
pub struct Cli {
    #[clap(
        long,
        help = "Log level, supported 'info', 'debug', 'warning'",
        default_value = "info"
    )]
    pub log_level: String,

    #[clap(long, help = "Dev.to api url", default_value = "https://dev.to/api/")]
    pub dev_to_url: Url,

    #[clap(long, help = "Dev.to page size", default_value = "10")]
    pub dev_to_page: u8,
}
