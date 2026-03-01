alter table receipt_sources
  add column raw_html text,
  add column pdf_urls text[];
