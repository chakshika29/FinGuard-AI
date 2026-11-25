// ============================================================================
// FinGuard AI - Power Query M Script (BigQuery Mode & Local CSV Fallback)
// Replace <GCP_PROJECT_ID> or <LOCAL_EXPORT_PATH> for your environment.
// ============================================================================

// Option A: Google BigQuery Direct Connector (Curated Transactions)
let
    Source = GoogleBigQuery.Database([BillingProject="<GCP_PROJECT_ID>"]),
    ProjectNav = Source{[Name="<GCP_PROJECT_ID>"]}[Data],
    CuratedDataset = ProjectNav{[Name="finguard_curated",Kind="Schema"]}[Data],
    TransactionsTable = CuratedDataset{[Name="transactions",Kind="Table"]}[Data],
    MaskedCard = Table.TransformColumns(
        TransactionsTable,
        {{"card_token", each "****" & Text.End(Text.From(_), 4), type text}}
    )
in
    MaskedCard

// Option B: Local CSV Fallback (fact_transactions.csv)
/*
let
    Source = Csv.Document(
        File.Contents("C:\Users\Dell\Desktop\FinGuard-AI\powerbi\datasets\fact_transactions.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"transaction_amount", type number},
            {"fraud_risk_score", type number},
            {"transaction_date", type date},
            {"credit_limit", type number},
            {"outstanding_balance", type number}
        }
    )
in
    TypedTable
*/
