# Tests :

https://www.quebec.ca/sante/problemes-de-sante/a-z/coronavirus-2019/reponses-questions-coronavirus-covid19/isolement-symptomes-traitements-covid-19/#c54105

- Existe il un vaccin pour le covid-19 // bad QA but doc in the 10
- Existe-t-il un traitement contre la COVID‑19 ?
- Est-ce qu'il existe un vaccin contre le COVID-19 // Good answer

- Multi chunk appears many time (because of title)

# Done :

- Computing on GPU 200s vs 600 for cpu

# Doing :

- Test embdding all vs sentence
- Better filter / Election (Ex : question "Plop" returns documents)
- Boost by date or other fields

# Ideas :

- Add NER to retrieve voc with same semantic structure
- Move the clear_database button further from the ask button (stupid missclick)

# TLDR :

- Question working good if well formulated, the rest is still returning crap -> need better cleaning and election
