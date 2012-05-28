species_list = container.Art17species()

def execute_query(q_number, query_text):
    if q_number == 1:
        #returns: {GROUP:(SPECNUM, SPECNAME)} if ANNEX_II or ANNEX_IV or ANNEXV
        res = {}
        for spec in species_list:
            if  spec[6] or spec[7] or spec[8]:
                if res.has_key(spec[0]):
                    res[spec[0]].append((spec[4], spec[3]))
                else:
                    res[spec[0]] = [(spec[4], spec[3])]
    if q_number == 2:
        #returns: {GROUP:(SPECNUM, SPECNAME)} if ANNEX_II or ANNEX_IV or ANNEXV containing QUERY_TEXT
        res = {}
        query_text = query_text.lower()
        for spec in species_list:
            if  (spec[6] or spec[7] or spec[8]) and (query_text in spec[3].lower() or query_text in spec[4].lower()):
                if res.has_key(spec[0]):
                    res[spec[0]].append((spec[4], spec[3]))
                else:
                    res[spec[0]] = [(spec[4], spec[3])]
    if q_number == 3:
        #returns: (SPECNUM, SPECNAME) if ANNEX_II or ANNEX_IV or ANNEXV
        res = [(spec[4],spec[3]) for spec in species_list if spec[6] or spec[7] or spec[8]]
    if q_number == 4:
        #returns: {GROUP:(SPECNUM, SPECNAME)} if ANNEX_IV containing QUERY_TEXT
        res = {}
        query_text = query_text.lower()
        for spec in species_list:
            if  spec[7] and (query_text in spec[3].lower() or query_text in spec[4].lower()):
                if res.has_key(spec[0]):
                    res[spec[0]].append((spec[4], spec[3]))
                else:
                    res[spec[0]] = [(spec[4], spec[3])]

    return res

return execute_query(query_number, query_text)
