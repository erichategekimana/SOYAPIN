# SOYAPIN
Online shopping app that sells product related to Soya beans
Team_Setup_and_Project_Planning$ tree
.
├── actions
│   ├── export_json.sh
│   ├── run_etl.sh
│   └── serve_frontend.sh
├── api
│   ├── app.py
│   ├── db.py
│   ├── schemas.py
│   └── server.py
├── data
│   ├── db.sqlite3
│   ├── logs
│   │   ├── etl_logs
│   │   │   └── etl.log
│   │   └── unsupported_files
│   ├── processed
│   │   └── dashboard.json
│   └── raw
│       └── momo_file.xml
├── database
│   ├── CRUD_operations.txt
│   ├── database_setup.sql
│   └── sample_data.sql
├── docs
│   └── erd_diagram.pdf
├── etl
│   ├── clean_narmalize.py
│   ├── config.py
│   ├── load_db.py
│   ├── parse_xml.py
│   └── run.py
├── examples
│   ├── complete_transaction.json
│   ├── customer.json
│   ├── system_logs.json
│   ├── transaction_categories.json
│   └── transactions.json
├── README.md
├── requirements.txt
└── web
    ├── index.html
    ├── script.js
    └── styles.css


