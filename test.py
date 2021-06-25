import csv

with open('static/templates/cards.csv', 'r') as csvfile:

    print('Reading cards.csv...')
    csv_reader = csv.reader(csvfile)

    db.execute("CREATE TABLE IF NOT EXISTS cards ( \        
        suit VARCHAR (255), \
        card VARCHAR (255), \
        number INTEGER, \
        symbol VARCHAR (255), \
        text VARCHAR (4096) \
        )")

    db.execute("DELETE from cards")

    for row in csv_reader:
        db.execute("INSERT INTO cards (suit, card, number, symbol, text) VALUES (:suit, :card, :number, :symbol, :text)", \
                        suit=row[0], card=row[1], number=row[2], symbol=row[3], text=row[4])

return render_template('message.html', message="Success, loterias updated.")
