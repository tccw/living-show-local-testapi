#!/bin/bash

# Reset the database by removing all data except the three default entries
echo "Resetting the database..."
sqlite3 app/data.db "DELETE FROM records WHERE id > 984";
sqlite3 app/data.db "DELETE FROM photos WHERE CAST(uri AS INT) > 658";