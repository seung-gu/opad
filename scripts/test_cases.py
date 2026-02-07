"""Test cases for lemma extraction accuracy testing.

Format: (sentence, word, expected_lemma, expected_related_words, category)
"""

# ═══════════════════════════════════════════════════════════════════════════════
# GERMAN TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

TEST_CASES_DE = [
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. 분리동사 (Separable Verbs)
    # ═══════════════════════════════════════════════════════════════════════════

    # --- 기본 분리동사 (문장 끝 접두사) ---
    ("Diese große Spanne hängt von mehreren Faktoren ab.", "hängt", "abhängen", ["hängt", "ab"], "분리동사"),
    ("Das Bekennerschreiben der Gruppe wirft Fragen auf.", "wirft", "aufwerfen", ["wirft", "auf"], "분리동사"),
    ("Er hört mit dem Rauchen auf.", "hört", "aufhören", ["hört", "auf"], "분리동사"),
    ("Das Spiel fängt um 8 an.", "fängt", "anfangen", ["fängt", "an"], "분리동사"),
    ("Die Sonne geht unter.", "geht", "untergehen", ["geht", "unter"], "분리동사"),
    ("Er steigt in den Bus ein.", "steigt", "einsteigen", ["steigt", "ein"], "분리동사"),
    ("Der Zug fährt um 9 ab.", "fährt", "abfahren", ["fährt", "ab"], "분리동사"),
    ("Sie räumt das Zimmer auf.", "räumt", "aufräumen", ["räumt", "auf"], "분리동사"),
    ("Er nimmt an dem Kurs teil.", "nimmt", "teilnehmen", ["nimmt", "teil"], "분리동사"),
    ("Sie sieht sehr müde aus.", "sieht", "aussehen", ["sieht", "aus"], "분리동사"),
    ("Er bringt das Buch zurück.", "bringt", "zurückbringen", ["bringt", "zurück"], "분리동사"),

    # --- 분리동사 (zu + Infinitiv 형태) ---
    ("Es fand am Nürburgring statt, einer sehr bekannten Rennstrecke in Deutschland.", "fand", "stattfinden", ["fand", "statt"], "분리동사"),
    ("Sollten Sie einen bestimmten Artikel auswählen, passe ich diesen gerne an.", "passe", "anpassen", ["passe", "an"], "분리동사"),
    ("Den Ausbau öffentlicher Ladepunkte voranzutreiben ist wichtig.", "voranzutreiben", "vorantreiben", ["voranzutreiben"], "분리동사"),

    # --- 분리동사 (비분리 형태 - 부문장/zu-Infinitiv) ---
    ("Wichtig ist, bei der Auswahl des VPN-Anbieters darauf zu achten, welche Protokolle er anbietet.", "anbietet", "anbieten", ["anbietet"], "분리동사"),
    ("Er versucht, seine Freundin abzuholen.", "abzuholen", "abholen", ["abzuholen"], "분리동사"),
    ("Es ist schwer, früh aufzustehen.", "aufzustehen", "aufstehen", ["aufzustehen"], "분리동사"),
    ("Sie hat vor, morgen anzurufen.", "anzurufen", "anrufen", ["anzurufen"], "분리동사"),
    ("Er hofft, bald zurückzukommen.", "zurückzukommen", "zurückkommen", ["zurückzukommen"], "분리동사"),
    ("Es ist wichtig, rechtzeitig anzufangen.", "anzufangen", "anfangen", ["anzufangen"], "분리동사"),

    # --- 분리동사 (종속절 - dass/weil/wenn/ob/als/bevor 등) ---
    ("Ich weiß, dass er früh aufsteht.", "aufsteht", "aufstehen", ["aufsteht"], "분리동사"),
    ("Sie sagt, dass sie morgen ankommt.", "ankommt", "ankommen", ["ankommt"], "분리동사"),
    ("Er fragt, ob sie heute mitkommt.", "mitkommt", "mitkommen", ["mitkommt"], "분리동사"),
    ("Ich bin froh, weil er endlich aufhört.", "aufhört", "aufhören", ["aufhört"], "분리동사"),
    ("Sie wartet, bis der Zug abfährt.", "abfährt", "abfahren", ["abfährt"], "분리동사"),
    ("Er wusste nicht, dass sie zurückkommt.", "zurückkommt", "zurückkommen", ["zurückkommt"], "분리동사"),
    ("Bevor er einkauft, macht er eine Liste.", "einkauft", "einkaufen", ["einkauft"], "분리동사"),
    ("Als er aufwachte, war es schon hell.", "aufwachte", "aufwachen", ["aufwachte"], "분리동사"),
    ("Wenn sie anruft, bin ich nicht da.", "anruft", "anrufen", ["anruft"], "분리동사"),
    ("Obwohl er aussieht wie ein Kind, ist er erwachsen.", "aussieht", "aussehen", ["aussieht"], "분리동사"),
    ("Nachdem er einsteigt, fährt der Bus los.", "einsteigt", "einsteigen", ["einsteigt"], "분리동사"),
    ("Während sie einkauft, wartet er draußen.", "einkauft", "einkaufen", ["einkauft"], "분리동사"),

    # --- 분리동사 (조동사 + 분리동사 - 원형으로 붙어있음) ---
    ("Er muss früh aufstehen.", "aufstehen", "aufstehen", ["aufstehen"], "분리동사"),
    ("Sie will morgen ankommen.", "ankommen", "ankommen", ["ankommen"], "분리동사"),
    ("Wir können heute anfangen.", "anfangen", "anfangen", ["anfangen"], "분리동사"),
    ("Er soll das Licht ausmachen.", "ausmachen", "ausmachen", ["ausmachen"], "분리동사"),
    ("Sie darf nicht mitkommen.", "mitkommen", "mitkommen", ["mitkommen"], "분리동사"),

    # --- 분리동사 (prefix 뒤에 쉼표 - 주절 + 종속절) ---
    ("Er steht früh auf, weil er arbeiten muss.", "steht", "aufstehen", ["steht", "auf"], "분리동사"),
    ("Sie kommt morgen an, wenn das Wetter gut ist.", "kommt", "ankommen", ["kommt", "an"], "분리동사"),
    ("Der Film fängt um 8 an, aber ich komme später.", "fängt", "anfangen", ["fängt", "an"], "분리동사"),
    ("Er hört mit dem Rauchen auf, weil es ungesund ist.", "hört", "aufhören", ["hört", "auf"], "분리동사"),
    ("Sie räumt das Zimmer auf, bevor die Gäste kommen.", "räumt", "aufräumen", ["räumt", "auf"], "분리동사"),
    ("Er nimmt an dem Kurs teil, obwohl er wenig Zeit hat.", "nimmt", "teilnehmen", ["nimmt", "teil"], "분리동사"),
    ("Die Sonne geht unter, während wir spazieren gehen.", "geht", "untergehen", ["geht", "unter"], "분리동사"),
    ("Er bringt das Buch zurück, sobald er es gelesen hat.", "bringt", "zurückbringen", ["bringt", "zurück"], "분리동사"),

    # --- 분리동사 (과거분사) ---
    ("Der Film hat um 20 Uhr angefangen.", "angefangen", "anfangen", ["angefangen"], "분리동사"),
    ("Sie hat das Licht ausgemacht.", "ausgemacht", "ausmachen", ["ausgemacht"], "분리동사"),
    ("Er ist gestern zurückgekommen.", "zurückgekommen", "zurückkommen", ["zurückgekommen"], "분리동사"),

    # --- 분리동사 (접두사 클릭) - 동사가 아니라 prefix를 클릭해도 lemma 반환 ---
    ("Er hört mit dem Rauchen auf.", "auf", "aufhören", ["hört", "auf"], "분리동사"),
    ("Der Zug fährt um 9 ab.", "ab", "abfahren", ["fährt", "ab"], "분리동사"),
    ("Das Spiel fängt um 8 an.", "an", "anfangen", ["fängt", "an"], "분리동사"),
    ("Die Sonne geht unter.", "unter", "untergehen", ["geht", "unter"], "분리동사"),
    ("Er steigt in den Bus ein.", "ein", "einsteigen", ["steigt", "ein"], "분리동사"),
    ("Er nimmt an dem Kurs teil.", "teil", "teilnehmen", ["nimmt", "teil"], "분리동사"),
    ("Sie sieht sehr müde aus.", "aus", "aussehen", ["sieht", "aus"], "분리동사"),
    ("Er bringt das Buch zurück.", "zurück", "zurückbringen", ["bringt", "zurück"], "분리동사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. 재귀동사 (Reflexive Verbs) - 다양한 재귀대명사 포함
    # ═══════════════════════════════════════════════════════════════════════════

    # --- sich (3인칭) ---
    ("Die Bevölkerung informiert sich jetzt stärker über Möglichkeiten der Online-Sicherheit.", "informiert", "sich informieren", ["informiert", "sich"], "재귀동사"),
    ("Sie freut sich auf den Skiurlaub in den Alpen nächste Woche.", "freut", "sich freuen", ["freut", "sich"], "재귀동사"),
    ("Er interessiert sich seit Jahren für klassische Musik und besucht oft Konzerte.", "interessiert", "sich interessieren", ["interessiert", "sich"], "재귀동사"),
    ("Sie erinnert sich noch genau an den Tag, als sie ihren Führerschein gemacht hat.", "erinnert", "sich erinnern", ["erinnert", "sich"], "재귀동사"),
    ("Nach der langen Wanderung fühlt sie sich erschöpft und will nur noch schlafen.", "fühlt", "sich fühlen", ["fühlt", "sich"], "재귀동사"),
    ("Er konzentriert sich auf die Steuererklärung, obwohl die Kinder laut spielen.", "konzentriert", "sich konzentrieren", ["konzentriert", "sich"], "재귀동사"),

    # --- mich (1인칭 단수 Akkusativ) ---
    ("Ich wasche mich nach dem Training unter der Dusche.", "wasche", "sich waschen", ["wasche", "mich"], "재귀동사"),
    ("Ich freue mich auf das lange Wochenende, weil wir endlich wandern gehen.", "freue", "sich freuen", ["freue", "mich"], "재귀동사"),
    ("Ich erinnere mich noch gut an unseren Sommerurlaub am Mittelmeer.", "erinnere", "sich erinnern", ["erinnere", "mich"], "재귀동사"),
    ("Nach dem Arztbesuch fühle ich mich deutlich besser als gestern.", "fühle", "sich fühlen", ["fühle", "mich"], "재귀동사"),

    # --- uns (1인칭 복수) ---
    ("Wir freuen uns auf die Sommerferien in Italien.", "freuen", "sich freuen", ["freuen", "uns"], "재귀동사"),
    ("Wir treffen uns um 8 Uhr vor dem Kino, um den neuen Film zu sehen.", "treffen", "sich treffen", ["treffen", "uns"], "재귀동사"),
    ("Wir erinnern uns gern an die gemeinsame Schulzeit in Hamburg.", "erinnern", "sich erinnern", ["erinnern", "uns"], "재귀동사"),

    # --- dich (2인칭 단수 Akkusativ) ---
    ("Du freust dich über das Geburtstagsgeschenk von deiner Schwester.", "freust", "sich freuen", ["freust", "dich"], "재귀동사"),
    ("Du wäschst dich nach dem Fußballtraining immer viel zu langsam.", "wäschst", "sich waschen", ["wäschst", "dich"], "재귀동사"),

    # --- euch (2인칭 복수) ---
    ("Ihr freut euch bestimmt auf den Schulausflug nach München.", "freut", "sich freuen", ["freut", "euch"], "재귀동사"),
    ("Trefft ihr euch morgen Nachmittag im Café am Marktplatz?", "Trefft", "sich treffen", ["Trefft", "euch"], "재귀동사"),

    # --- 재귀대명사가 동사 앞에 오는 경우 (종속절) ---
    ("Ich weiß, dass er sich sehr über die Beförderung freut.", "freut", "sich freuen", ["sich", "freut"], "재귀동사"),
    ("Sie sagt, dass sie sich nach der Operation wieder gut fühlt.", "fühlt", "sich fühlen", ["sich", "fühlt"], "재귀동사"),
    ("Er fragt, ob sie sich noch an das Passwort erinnert.", "erinnert", "sich erinnern", ["sich", "erinnert"], "재귀동사"),
    ("Ich hoffe, dass du dich nach der Grippe bald erholst.", "erholst", "sich erholen", ["dich", "erholst"], "재귀동사"),
    ("Wir wissen, dass ihr euch nächsten Samstag zum Grillen trefft.", "trefft", "sich treffen", ["euch", "trefft"], "재귀동사"),
    ("Er meint, dass wir uns bei der Berechnung der Kosten irren.", "irren", "sich irren", ["uns", "irren"], "재귀동사"),
    ("Sie glaubt, dass ich mich wegen des Staus zum Meeting verspäte.", "verspäte", "sich verspäten", ["mich", "verspäte"], "재귀동사"),
    ("Ich bin froh, dass er sich für den unhöflichen Kommentar entschuldigt hat.", "entschuldigt", "sich entschuldigen", ["sich", "entschuldigt"], "재귀동사"),

    # --- 재귀대명사가 동사 앞에 오는 경우 (조동사 + Infinitiv) ---
    ("Er kann sich nach dem Unfall nicht mehr an die Adresse erinnern.", "erinnern", "sich erinnern", ["sich", "erinnern"], "재귀동사"),
    ("Der Zug fährt in fünf Minuten — sie muss sich beeilen.", "beeilen", "sich beeilen", ["sich", "beeilen"], "재귀동사"),
    ("Wir sollten uns am Wochenende zum Brunch im neuen Restaurant treffen.", "treffen", "sich treffen", ["uns", "treffen"], "재귀동사"),
    ("Du darfst dich wegen der schlechten Note nicht so aufregen.", "aufregen", "sich aufregen", ["dich", "aufregen"], "재귀동사"),
    ("Das Essen im Hotel war kalt — ich will mich an der Rezeption beschweren.", "beschweren", "sich beschweren", ["mich", "beschweren"], "재귀동사"),
    ("Ihr müsst euch bei der Matheprüfung nächste Woche mehr anstrengen.", "anstrengen", "sich anstrengen", ["euch", "anstrengen"], "재귀동사"),
    ("Man sollte sich regelmäßig bewegen, um Rückenschmerzen vorzubeugen.", "bewegen", "sich bewegen", ["sich", "bewegen"], "재귀동사"),
    ("Er möchte sich bei dem neuen Team als Projektleiter vorstellen.", "vorstellen", "sich vorstellen", ["sich", "vorstellen"], "재귀동사"),

    # --- 재귀대명사가 동사 앞에 오는 경우 (zu-Infinitiv) ---
    ("Bei der lauten Baustelle nebenan ist es schwer, sich auf die Arbeit zu konzentrieren.", "konzentrieren", "sich konzentrieren", ["sich", "konzentrieren"], "재귀동사"),
    ("Er versucht, sich an den Namen des Restaurants zu erinnern.", "erinnern", "sich erinnern", ["sich", "erinnern"], "재귀동사"),
    ("Nach dem Studium hat sie vor, sich bei einem großen Unternehmen zu bewerben.", "bewerben", "sich bewerben", ["sich", "bewerben"], "재귀동사"),
    ("Bei so vielen guten Optionen fällt es mir schwer, mich für ein Gericht zu entscheiden.", "entscheiden", "sich entscheiden", ["mich", "entscheiden"], "재귀동사"),
    ("Wir planen, uns nächsten Freitag nach der Arbeit im Park zu treffen.", "treffen", "sich treffen", ["uns", "treffen"], "재귀동사"),
    ("Er vergisst oft, sich bei seiner Mutter zu melden, wenn er auf Reisen ist.", "melden", "sich melden", ["sich", "melden"], "재귀동사"),

    # --- 재귀동사 + 분리동사 복합 ---
    ("Sie sprechen sich dafür aus, die Absicherung zu verbessern.", "sprechen", "sich aussprechen", ["sprechen", "sich", "aus"], "재귀동사+분리"),
    ("Bürger können sich schnell und ohne komplizierte Passwörter anmelden.", "anmelden", "sich anmelden", ["sich", "anmelden"], "재귀동사+분리"),
    ("Er kann sich vorstellen, als Teamchef zu arbeiten.", "vorstellen", "sich vorstellen", ["sich", "vorstellen"], "재귀동사+분리"),
    ("Er meldet sich bei der Konferenz an.", "meldet", "sich anmelden", ["meldet", "sich", "an"], "재귀동사+분리"),
    ("Ich melde mich für den Kurs an.", "melde", "sich anmelden", ["melde", "mich", "an"], "재귀동사+분리"),
    ("Wir melden uns morgen für den Sprachkurs an der Volkshochschule an.", "melden", "sich anmelden", ["melden", "uns", "an"], "재귀동사+분리"),

    # --- 재귀동사 + 분리동사 복합 (재귀대명사가 먼저) ---
    ("Ich weiß, dass er sich morgen anmeldet.", "anmeldet", "sich anmelden", ["sich", "anmeldet"], "재귀동사+분리"),
    ("Sie hofft, dass wir uns bald wiedersehen.", "wiedersehen", "sich wiedersehen", ["uns", "wiedersehen"], "재귀동사+분리"),
    ("Er muss sich warm anziehen.", "anziehen", "sich anziehen", ["sich", "anziehen"], "재귀동사+분리"),
    ("Du solltest dich hinsetzen.", "hinsetzen", "sich hinsetzen", ["dich", "hinsetzen"], "재귀동사+분리"),
    ("Wir wollen uns ausruhen.", "ausruhen", "sich ausruhen", ["uns", "ausruhen"], "재귀동사+분리"),
    ("Nach dem Schwimmen ist es Zeit, sich in der Umkleidekabine umzuziehen.", "umzuziehen", "sich umziehen", ["sich", "umzuziehen"], "재귀동사+분리"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. 오추론 방지 (False Positive Prevention) ⭐ 가장 중요
    # ═══════════════════════════════════════════════════════════════════════════

    # --- 전치사로 끝나지만 분리동사 아님 (nach/auf/an/aus/mit/vor/zu 전치사) ---
    ("Er fährt mit dem Auto nach Berlin.", "fährt", "fahren", ["fährt"], "오추론방지"),
    ("Sie kommt aus Deutschland.", "kommt", "kommen", ["kommt"], "오추론방지"),
    ("Er geht mit dem Hund spazieren.", "geht", "gehen", ["geht"], "오추론방지"),
    ("Sie spricht über das Thema.", "spricht", "sprechen", ["spricht"], "오추론방지"),
    ("Das Buch liegt auf dem Tisch.", "liegt", "liegen", ["liegt"], "오추론방지"),
    ("Wir fahren nach München.", "fahren", "fahren", ["fahren"], "오추론방지"),
    ("Sie arbeitet an einem Projekt.", "arbeitet", "arbeiten", ["arbeitet"], "오추론방지"),
    ("Er wartet auf den Bus.", "wartet", "warten", ["wartet"], "오추론방지"),
    ("Sie denkt an ihre Familie.", "denkt", "denken", ["denkt"], "오추론방지"),
    ("Er läuft durch den Park.", "läuft", "laufen", ["läuft"], "오추론방지"),

    # --- 문장 끝에 명사/형용사가 있는 경우 ---
    ("Er verdient sein Geld mit dem Rennfahren.", "verdient", "verdienen", ["verdient"], "오추론방지"),
    ("Sie geht in den Garten.", "geht", "gehen", ["geht"], "오추론방지"),
    ("Er sieht den neuen Film im Kino mit seinen Freunden.", "sieht", "sehen", ["sieht"], "오추론방지"),
    ("Sie hört die laute Musik aus dem Nachbarzimmer, obwohl sie schlafen will.", "hört", "hören", ["hört"], "오추론방지"),
    ("Er macht die Hausaufgaben am Küchentisch, bevor er nach draußen geht.", "macht", "machen", ["macht"], "오추론방지"),

    # --- 비분리 접두사 동사 (be-, ge-, er-, ver-, zer-, ent-, emp-, miss-) ---
    ("Er bekommt einen Brief.", "bekommt", "bekommen", ["bekommt"], "오추론방지"),
    ("Sie versteht das Problem.", "versteht", "verstehen", ["versteht"], "오추론방지"),
    ("Er erkennt seinen Fehler.", "erkennt", "erkennen", ["erkennt"], "오추론방지"),
    ("Sie beginnt mit der Arbeit.", "beginnt", "beginnen", ["beginnt"], "오추론방지"),
    ("Er vergisst ständig den Zahnarzttermin und muss immer wieder neu buchen.", "vergisst", "vergessen", ["vergisst"], "오추론방지"),

    # --- sich가 있지만 재귀동사가 아닌 경우 ---
    ("Das Kind wäscht sich nach dem Spielen im Garten die Hände.", "wäscht", "sich waschen", ["wäscht", "sich"], "재귀동사"),  # 이건 맞는 재귀동사
    ("Er gibt sich Mühe, die komplizierten Matheaufgaben zu lösen.", "gibt", "sich Mühe geben", ["gibt", "sich", "Mühe"], "오추론방지"),  # 관용구

    # --- 복합 함정: 문장에 분리접두사처럼 보이는 단어가 있지만 다른 용도 ---
    ("Er steht vor dem Haus.", "steht", "stehen", ["steht"], "오추론방지"),  # vor는 전치사
    ("Sie sitzt an dem Tisch.", "sitzt", "sitzen", ["sitzt"], "오추론방지"),  # an은 전치사
    ("Das Paket kommt aus China.", "kommt", "kommen", ["kommt"], "오추론방지"),  # aus는 전치사

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. 일반 동사 (Regular Verbs)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Die Arbeit von Regisseur Trier wurde besonders gewürdigt.", "gewürdigt", "würdigen", ["gewürdigt"], "일반동사"),
    ("Das liegt an seinem schlanken Programmiercode, der die Überprüfung vereinfacht.", "vereinfacht", "vereinfachen", ["vereinfacht"], "일반동사"),
    ("Immer mehr Unternehmen setzen auf diese Methode, um das digitale Leben sicherer zu gestalten.", "gestalten", "gestalten", ["gestalten"], "일반동사"),
    ("Für Unternehmen bedeutet das eine deutliche Verbesserung des Schutzes.", "bedeutet", "bedeuten", ["bedeutet"], "일반동사"),
    ("Der Student muss die schwierige Abschlussprüfung bestehen, um sein Diplom zu erhalten.", "bestehen", "bestehen", ["bestehen"], "일반동사"),
    ("Die Behörden wollen solche Vorfälle in Zukunft verhindern.", "verhindern", "verhindern", ["verhindern"], "일반동사"),
    ("Max Verstappen hat Geschichte geschrieben.", "geschrieben", "schreiben", ["geschrieben"], "일반동사"),
    ("Die richtige Auswahl kann darüber entscheiden, wie gut Ihre Daten geschützt sind.", "entscheiden", "entscheiden", ["entscheiden"], "일반동사"),
    ("Dadurch wird ein sehr sicheres Anmeldeverfahren geschaffen.", "geschaffen", "schaffen", ["geschaffen"], "일반동사"),
    ("Red Bull gilt momentan als das dominanteste Team.", "gilt", "gelten", ["gilt"], "일반동사"),
    ("Sie liest jeden Tag die Zeitung.", "liest", "lesen", ["liest"], "일반동사"),
    ("Er trinkt seinen Kaffee.", "trinkt", "trinken", ["trinkt"], "일반동사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. 명사 (Nouns)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Die Deutsche Gesellschaft für Cybersicherheit sieht Passkeys als wichtigen Schritt.", "Gesellschaft", "Gesellschaft", ["Gesellschaft"], "명사"),
    ("Bürger können leicht auf digitale Dienstleistungen zugreifen.", "Dienstleistungen", "Dienstleistung", ["Dienstleistungen"], "명사"),
    ("Trotz der vielen Vorteile gibt es auch einige Herausforderungen.", "Herausforderungen", "Herausforderung", ["Herausforderungen"], "명사"),
    ("Trotz der vielen Vorteile gibt es auch Herausforderungen.", "Vorteile", "Vorteil", ["Vorteile"], "명사"),
    ("Für Max Verstappen war dieser Sieg etwas ganz besonders.", "Sieg", "Sieg", ["Sieg"], "명사"),
    ("Das GT3-Rennen war für ihn eine neue Herausforderung.", "Herausforderung", "Herausforderung", ["Herausforderung"], "명사"),
    ("So kann er seine Erfolge und seinen guten Namen behalten.", "Erfolge", "Erfolg", ["Erfolge"], "명사"),
    ("Max Verstappen hat Geschichte geschrieben.", "Geschichte", "Geschichte", ["Geschichte"], "명사"),
    ("Für den Test haben die Techniker eine standardisierte Testbeladung verwendet.", "Techniker", "Techniker", ["Techniker"], "명사"),
    ("Deshalb sind Informationskampagnen und Schulungen notwendig.", "Informationskampagnen", "Informationskampagne", ["Informationskampagnen"], "명사"),
    # 관사 없이 반환해야 하는 케이스 (관사가 바로 앞에 있는 함정)
    ("Das Rennfahren ist spannend.", "Rennfahren", "Rennfahren", ["Rennfahren"], "명사"),
    ("Der Hund spielt im Garten.", "Hund", "Hund", ["Hund"], "명사"),
    ("Die Katze schläft auf dem Sofa.", "Katze", "Katze", ["Katze"], "명사"),
    ("Das Kind spielt draußen.", "Kind", "Kind", ["Kind"], "명사"),
    ("Der Lehrer erklärt die Aufgabe.", "Lehrer", "Lehrer", ["Lehrer"], "명사"),
    ("Sie liest ein Buch über die Geschichte des Römischen Reiches.", "Buch", "Buch", ["Buch"], "명사"),
    ("Er kauft einen neuen Wagen.", "Wagen", "Wagen", ["Wagen"], "명사"),
    # 관사가 먼 위치에 있는 경우
    ("In der kleinen Stadt gibt es eine alte Kirche.", "Kirche", "Kirche", ["Kirche"], "명사"),
    ("Mit dem schnellen Zug fahren wir nach Berlin.", "Zug", "Zug", ["Zug"], "명사"),
    # 복수형 + 관사
    ("Die Kinder spielen im Park.", "Kinder", "Kind", ["Kinder"], "명사"),
    ("Er hat die Bücher auf den Tisch gelegt.", "Bücher", "Buch", ["Bücher"], "명사"),

    # --- 성별에 따라 뜻이 다른 동형 명사 (다중 entry 발생) ---
    ("Der See ist im Winter zugefroren.", "See", "See", ["See"], "명사"),  # m = lake
    ("Die See war heute besonders ruhig.", "See", "See", ["See"], "명사"),  # f = sea
    ("Der Leiter des Unternehmens hielt eine Rede.", "Leiter", "Leiter", ["Leiter"], "명사"),  # m = leader
    ("Er stieg die Leiter hinauf.", "Leiter", "Leiter", ["Leiter"], "명사"),  # f = ladder
    ("Das Steuer des Autos war schwergängig.", "Steuer", "Steuer", ["Steuer"], "명사"),  # n = steering wheel
    ("Die Steuer auf Benzin wird erhöht.", "Steuer", "Steuer", ["Steuer"], "명사"),  # f = tax
    ("Der erste Band der Reihe ist vergriffen.", "Band", "Band", ["Band"], "명사"),  # m = volume
    ("Das Band zwischen ihnen ist stark.", "Band", "Band", ["Band"], "명사"),  # n = bond/ribbon
    ("Er hat das Tor zum 2:0 geschossen.", "Tor", "Tor", ["Tor"], "명사"),  # n = goal/gate
    ("Das Schild an der Tür war kaputt.", "Schild", "Schild", ["Schild"], "명사"),  # n = sign

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. 형용사 (Adjectives)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Doch damit Elektroautos praktisch genutzt werden können, braucht es eine gute zugängliche Infrastruktur.", "zugängliche", "zugänglich", ["zugängliche"], "형용사"),
    ("Passkeys sind eine Alternative für herkömmliche Passwörter.", "herkömmliche", "herkömmlich", ["herkömmliche"], "형용사"),
    ("Die Anmeldung erfolgt mit einem besonderen Sicherheitscode.", "besonderen", "besondere", ["besonderen"], "형용사"),
    ("Für den Test haben die Techniker eine standardisierte Testbeladung verwendet.", "standardisierte", "standardisiert", ["standardisierte"], "형용사"),
    ("Der berühmte Formel-1-Fahrer hat ein wichtiges Autorennen gewonnen.", "berühmte", "berühmt", ["berühmte"], "형용사"),
    ("Das zeigt, dass er ein kluger Mann ist.", "kluger", "klug", ["kluger"], "형용사"),
    ("Die nächsten Jahre werden sehr interessant.", "interessant", "interessant", ["interessant"], "형용사"),
    ("Sie wissen, dass er ein intelligenter Fahrer ist.", "intelligenter", "intelligent", ["intelligenter"], "형용사"),
    ("Das ist ein großes Haus.", "großes", "groß", ["großes"], "형용사"),
    ("Sie trägt ein rotes Kleid.", "rotes", "rot", ["rotes"], "형용사"),

    # --- 분사형 형용사 (API에서 verb + adjective 다중 entry 발생) ---
    ("Experten sind gespannt darauf, wie sich diese Entwicklung auswirken wird.", "gespannt", "gespannt", ["gespannt"], "형용사"),
    ("Die Konkurrenz zwischen verschiedenen KI-Modellen wird immer härter.", "verschiedenen", "verschieden", ["verschiedenen"], "형용사"),
    ("Viele befürchten, dass solche Systeme bestimmte Arbeitsplätze bedrohen könnten.", "bestimmte", "bestimmt", ["bestimmte"], "형용사"),
    ("Er ist ein bekannter Schauspieler in Deutschland.", "bekannter", "bekannt", ["bekannter"], "형용사"),
    ("Das war eine überraschende Wendung in der Geschichte.", "überraschende", "überraschend", ["überraschende"], "형용사"),
    ("Sie hat eine bedeutende Rolle in dem Film gespielt.", "bedeutende", "bedeutend", ["bedeutende"], "형용사"),
    ("Das Ergebnis war sehr enttäuschend für alle Beteiligten.", "enttäuschend", "enttäuschend", ["enttäuschend"], "형용사"),
    ("Er hat einen entscheidenden Beitrag zum Projekt geleistet.", "entscheidenden", "entscheidend", ["entscheidenden"], "형용사"),
    ("Die vergangenen Wochen waren sehr stressig.", "vergangenen", "vergangen", ["vergangenen"], "형용사"),
    ("Das ist ein ausgezeichnetes Restaurant.", "ausgezeichnetes", "ausgezeichnet", ["ausgezeichnetes"], "형용사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. 부사 (Adverbs)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Es war sein erstes GT3-Rennen überhaupt.", "überhaupt", "überhaupt", ["überhaupt"], "부사"),
    ("Außerdem gibt es trotz neuer Technologien immer noch Bereiche mit Personalmangel.", "Außerdem", "außerdem", ["Außerdem"], "부사"),
    ("Das Reisen zu den Rennen ist anstrengend.", "anstrengend", "anstrengend", ["anstrengend"], "부사"),
    ("Das geht leider nicht.", "leider", "leider", ["leider"], "부사"),
    ("Sie arbeitet hier.", "hier", "hier", ["hier"], "부사"),
    ("Er kommt heute.", "heute", "heute", ["heute"], "부사"),
    ("Sie singt sehr schön.", "schön", "schön", ["schön"], "부사"),
    ("Er läuft schnell.", "schnell", "schnell", ["schnell"], "부사"),

    # --- 품사 겸용 부사 (adjective/adverb 다중 entry 가능) ---
    ("Er hat das gerade erst erfahren.", "gerade", "gerade", ["gerade"], "부사"),
    ("Sie spricht besonders gut Englisch.", "besonders", "besonders", ["besonders"], "부사"),
    ("Er hat recht gut gespielt.", "recht", "recht", ["recht"], "부사"),
    ("Laut einer Studie ist das gefährlich.", "Laut", "laut", ["Laut"], "부사"),
    ("Sie hat ziemlich lange gewartet.", "ziemlich", "ziemlich", ["ziemlich"], "부사"),
    ("Er hat das völlig falsch verstanden.", "völlig", "völlig", ["völlig"], "부사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. 전치사 (Prepositions)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Er geht mit seinem Freund.", "mit", "mit", ["mit"], "전치사"),
    ("Das Buch liegt auf dem Tisch.", "auf", "auf", ["auf"], "전치사"),
    ("Sie kommt aus der Stadt.", "aus", "aus", ["aus"], "전치사"),
    ("Er fährt nach Hause.", "nach", "nach", ["nach"], "전치사"),
    ("Sie steht vor der Tür.", "vor", "vor", ["vor"], "전치사"),
    ("Er arbeitet für die Firma.", "für", "für", ["für"], "전치사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. 접속사 (Conjunctions)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Die Dreharbeiten waren nicht nur eine Herausforderung, sondern teilweise sogar lebensgefährlich.", "sondern", "sondern", ["sondern"], "접속사"),
    ("Er ist müde, weil er nicht geschlafen hat.", "weil", "weil", ["weil"], "접속사"),
    ("Ich weiß, dass er kommt.", "dass", "dass", ["dass"], "접속사"),
    ("Er liest und sie schreibt.", "und", "und", ["und"], "접속사"),
    ("Aber auch nach 2028 will er nicht mehr sehr lange weitermachen.", "Aber", "aber", ["Aber"], "접속사"),
    ("Er arbeitet, obwohl er krank ist.", "obwohl", "obwohl", ["obwohl"], "접속사"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 10. 관사 (Articles)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Der Hund läuft schnell.", "Der", "der", ["Der"], "관사"),
    ("Die Katze schläft.", "Die", "die", ["Die"], "관사"),
    ("Das Auto ist neu.", "Das", "das", ["Das"], "관사"),
]


# ═══════════════════════════════════════════════════════════════════════════════
# ENGLISH TEST CASES
# ═══════════════════════════════════════════════════════════════════════════════

TEST_CASES_EN = [
    # ═══════════════════════════════════════════════════════════════════════════
    # 1. Phrasal Verbs - 기본 (verb + particle 붙어있음)
    # ═══════════════════════════════════════════════════════════════════════════
    ("After years of struggling with addiction, she finally gave up smoking and started a healthier lifestyle.", "gave", "give up", ["gave", "up"], "phrasal verb"),
    ("The pilot announced that the plane would take off in approximately fifteen minutes.", "take", "take off", ["take", "off"], "phrasal verb"),
    ("When the negotiations failed, the company had no choice but to call off the merger.", "call", "call off", ["call", "off"], "phrasal verb"),
    ("The detective needed several hours to figure out who was responsible for the crime.", "figure", "figure out", ["figure", "out"], "phrasal verb"),
    ("Despite her best efforts to stay calm, she eventually broke down and started crying.", "broke", "break down", ["broke", "down"], "phrasal verb"),
    ("The meeting was supposed to start at nine, but the manager showed up thirty minutes late.", "showed", "show up", ["showed", "up"], "phrasal verb"),
    ("Scientists are still trying to find out what caused the mysterious phenomenon.", "find", "find out", ["find", "out"], "phrasal verb"),
    ("The professor asked the students to hand in their assignments before the deadline.", "hand", "hand in", ["hand", "in"], "phrasal verb"),
    ("After the long hike, everyone was exhausted and ready to sit down for a rest.", "sit", "sit down", ["sit", "down"], "phrasal verb"),
    ("The old factory was torn down to make room for a new shopping center.", "torn", "tear down", ["torn", "down"], "phrasal verb"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. Phrasal Verbs - 분리형 (목적어가 verb와 particle 사이)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Before leaving the house, he always turns the lights off to save electricity.", "turns", "turn off", ["turns", "off"], "phrasal verb separated"),
    ("The teacher asked the students to put their phones away during the exam.", "put", "put away", ["put", "away"], "phrasal verb separated"),
    ("She picked her children up from school every day at three o'clock.", "picked", "pick up", ["picked", "up"], "phrasal verb separated"),
    ("He took his jacket off because the room was getting too warm.", "took", "take off", ["took", "off"], "phrasal verb separated"),
    ("The manager called the meeting off due to unexpected circumstances.", "called", "call off", ["called", "off"], "phrasal verb separated"),
    ("I finally figured the puzzle out after thinking about it for hours.", "figured", "figure out", ["figured", "out"], "phrasal verb separated"),
    ("She threw the old newspapers away because they were taking up too much space.", "threw", "throw away", ["threw", "away"], "phrasal verb separated"),
    ("The workers tore the old building down in just three days.", "tore", "tear down", ["tore", "down"], "phrasal verb separated"),
    ("He turned the volume up so everyone in the room could hear the music.", "turned", "turn up", ["turned", "up"], "phrasal verb separated"),
    ("She looked the information up in the encyclopedia before writing her essay.", "looked", "look up", ["looked", "up"], "phrasal verb separated"),
    ("The company laid several employees off due to budget constraints.", "laid", "lay off", ["laid", "off"], "phrasal verb separated"),
    ("Please fill this form out and return it to the reception desk.", "fill", "fill out", ["fill", "out"], "phrasal verb separated"),
    ("He crossed the wrong answer out and wrote the correct one.", "crossed", "cross out", ["crossed", "out"], "phrasal verb separated"),
    ("The teacher handed the exams back after grading them over the weekend.", "handed", "hand back", ["handed", "back"], "phrasal verb separated"),
    ("We need to sort these documents out before the audit next week.", "sort", "sort out", ["sort", "out"], "phrasal verb separated"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. Phrasal Verbs - Particle 클릭
    # ═══════════════════════════════════════════════════════════════════════════
    ("She gave up smoking after twenty years.", "up", "give up", ["gave", "up"], "phrasal verb particle"),
    ("He turned the computer off before leaving.", "off", "turn off", ["turned", "off"], "phrasal verb particle"),
    ("The plane took off from the runway.", "off", "take off", ["took", "off"], "phrasal verb particle"),
    ("She picked her keys up from the table.", "up", "pick up", ["picked", "up"], "phrasal verb particle"),
    ("They called the event off at the last minute.", "off", "call off", ["called", "off"], "phrasal verb particle"),
    ("He threw the garbage away after breakfast.", "away", "throw away", ["threw", "away"], "phrasal verb particle"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. 오추론 방지 - 전치사로 끝나지만 phrasal verb 아님
    # ═══════════════════════════════════════════════════════════════════════════
    ("After finishing her work, she walked to the park for some fresh air.", "walked", "walk", ["walked"], "false positive"),
    ("The tourists spent hours looking at the beautiful paintings in the museum.", "looking", "look", ["looking"], "false positive"),
    ("I've been thinking about your proposal and I have some concerns.", "thinking", "think", ["thinking"], "false positive"),
    ("He drove to work every day despite the heavy traffic.", "drove", "drive", ["drove"], "false positive"),
    ("She talked to her supervisor about the upcoming project deadline.", "talked", "talk", ["talked"], "false positive"),
    ("The children ran to the playground as soon as the bell rang.", "ran", "run", ["ran"], "false positive"),
    ("He listened to the entire lecture without taking any notes.", "listened", "listen", ["listened"], "false positive"),
    ("She waited for the bus in the cold for almost an hour.", "waited", "wait", ["waited"], "false positive"),
    ("They agreed to the terms of the contract after lengthy negotiations.", "agreed", "agree", ["agreed"], "false positive"),
    ("The cat jumped on the couch and immediately fell asleep.", "jumped", "jump", ["jumped"], "false positive"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. 일반 동사 (Regular Verbs)
    # ═══════════════════════════════════════════════════════════════════════════
    ("Despite the rain, she runs five kilometers every morning before breakfast.", "runs", "run", ["runs"], "verb"),
    ("The famous author writes at least two thousand words every day.", "writes", "write", ["writes"], "verb"),
    ("They have finished renovating the entire house after six months of work.", "finished", "finish", ["finished"], "verb"),
    ("I am reading an interesting book about the history of ancient civilizations.", "reading", "read", ["reading"], "verb"),
    ("She has been working on this project for the past three months.", "working", "work", ["working"], "verb"),
    ("The company manufactures electronic components for major smartphone brands.", "manufactures", "manufacture", ["manufactures"], "verb"),
    ("He studies medicine at one of the most prestigious universities in the country.", "studies", "study", ["studies"], "verb"),
    ("The chef prepares a special menu for the restaurant every weekend.", "prepares", "prepare", ["prepares"], "verb"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. 불규칙 동사 (Irregular Verbs)
    # ═══════════════════════════════════════════════════════════════════════════
    ("He went to the grocery store to buy some vegetables for dinner.", "went", "go", ["went"], "irregular verb"),
    ("The author has written more than twenty bestselling novels in her career.", "written", "write", ["written"], "irregular verb"),
    ("I saw the northern lights for the first time during my trip to Iceland.", "saw", "see", ["saw"], "irregular verb"),
    ("They have been friends since they were in elementary school together.", "been", "be", ["been"], "irregular verb"),
    ("She bought a beautiful antique vase at the auction last weekend.", "bought", "buy", ["bought"], "irregular verb"),
    ("He taught mathematics at the local high school for over thirty years.", "taught", "teach", ["taught"], "irregular verb"),
    ("I thought the movie was going to be boring, but it turned out to be excellent.", "thought", "think", ["thought"], "irregular verb"),
    ("She brought homemade cookies to the office party and everyone loved them.", "brought", "bring", ["brought"], "irregular verb"),
    ("The company sold more than a million units in the first quarter.", "sold", "sell", ["sold"], "irregular verb"),
    ("He caught the last train home just before the station closed.", "caught", "catch", ["caught"], "irregular verb"),
    ("The temperature fell below zero for the first time this winter.", "fell", "fall", ["fell"], "irregular verb"),
    ("She spoke fluently in five different languages by the age of twenty.", "spoke", "speak", ["spoke"], "irregular verb"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. 명사 (Nouns) - 불규칙 복수형 포함
    # ═══════════════════════════════════════════════════════════════════════════
    ("The children were playing in the backyard when it suddenly started to rain.", "children", "child", ["children"], "noun"),
    ("These women are leading researchers in the field of renewable energy.", "women", "woman", ["women"], "noun"),
    ("The mice escaped from the laboratory through a small hole in the wall.", "mice", "mouse", ["mice"], "noun"),
    ("His teeth were perfectly white after the professional cleaning treatment.", "teeth", "tooth", ["teeth"], "noun"),
    ("The books on the top shelf are first editions worth thousands of dollars.", "books", "book", ["books"], "noun"),
    ("She has many responsibilities as the head of the marketing department.", "responsibilities", "responsibility", ["responsibilities"], "noun"),
    ("The geese flew south for the winter in a perfect V formation.", "geese", "goose", ["geese"], "noun"),
    ("The leaves on the trees are starting to change color as autumn approaches.", "leaves", "leaf", ["leaves"], "noun"),
    ("The knives in the kitchen drawer need to be sharpened regularly.", "knives", "knife", ["knives"], "noun"),
    ("Several phenomena were observed during the scientific experiment.", "phenomena", "phenomenon", ["phenomena"], "noun"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. 형용사 (Adjectives) - 비교급/최상급 포함
    # ═══════════════════════════════════════════════════════════════════════════
    ("She is the tallest player on the basketball team by several inches.", "tallest", "tall", ["tallest"], "adjective"),
    ("This documentary is much more interesting than the one we watched yesterday.", "interesting", "interesting", ["interesting"], "adjective"),
    ("He looks happier today than he has in weeks.", "happier", "happy", ["happier"], "adjective"),
    ("It was the best vacation we have ever taken as a family.", "best", "good", ["best"], "adjective"),
    ("The weather today is worse than the forecast predicted.", "worse", "bad", ["worse"], "adjective"),
    ("This is the oldest building in the entire city, dating back to the 1700s.", "oldest", "old", ["oldest"], "adjective"),
    ("The new model is faster and more efficient than its predecessor.", "faster", "fast", ["faster"], "adjective"),
    ("She received the highest score on the exam in the entire class.", "highest", "high", ["highest"], "adjective"),

    # --- 동형이의어 형용사 (noun/verb와 동일 형태, 다중 entry 발생) ---
    ("The room was light and airy with large windows.", "light", "light", ["light"], "adjective"),
    ("She felt close to her grandmother despite the distance.", "close", "close", ["close"], "adjective"),
    ("He has a pretty good understanding of the topic.", "pretty", "pretty", ["pretty"], "adjective"),
    ("That was a fair decision by the referee.", "fair", "fair", ["fair"], "adjective"),
    ("The sound of the bell was very clear.", "clear", "clear", ["clear"], "adjective"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. 부사 (Adverbs)
    # ═══════════════════════════════════════════════════════════════════════════
    ("She runs quickly through the park every morning before sunrise.", "quickly", "quickly", ["quickly"], "adverb"),
    ("He spoke very softly so as not to wake the sleeping baby.", "softly", "softly", ["softly"], "adverb"),
    ("They arrived yesterday after a long journey across the country.", "yesterday", "yesterday", ["yesterday"], "adverb"),
    ("I will finish the report now and submit it before the deadline.", "now", "now", ["now"], "adverb"),
    ("The train moved slowly through the mountainous region.", "slowly", "slowly", ["slowly"], "adverb"),
    ("She always arrives early for important meetings.", "early", "early", ["early"], "adverb"),

    # --- 품사 겸용 부사 (adjective와 동일 형태, 다중 entry 발생) ---
    ("She ran fast to catch the bus.", "fast", "fast", ["fast"], "adverb"),
    ("He worked hard all day long.", "hard", "hard", ["hard"], "adverb"),
    ("Turn left at the traffic light and the hospital is on your right.", "left", "left", ["left"], "adverb"),
    ("She sang pretty well for her first performance.", "pretty", "pretty", ["pretty"], "adverb"),
    ("He still lives in the same house.", "still", "still", ["still"], "adverb"),
    ("She just arrived a few minutes ago.", "just", "just", ["just"], "adverb"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 10. 동형이의어 명사 (verb/adjective와 동일 형태, 다중 entry 발생)
    # ═══════════════════════════════════════════════════════════════════════════
    ("The morning run helped him clear his mind.", "run", "run", ["run"], "noun"),
    ("She turned on the light in the hallway.", "light", "light", ["light"], "noun"),
    ("He took a left at the intersection.", "left", "left", ["left"], "noun"),
    ("The play was a huge success on Broadway.", "play", "play", ["play"], "noun"),
    ("The match ended in a draw after extra time.", "match", "match", ["match"], "noun"),
    ("He made a fair point during the debate.", "point", "point", ["point"], "noun"),

    # ═══════════════════════════════════════════════════════════════════════════
    # 11. 전치사 & 접속사 (Prepositions & Conjunctions)
    # ═══════════════════════════════════════════════════════════════════════════
    ("The book you were looking for is on the table in the living room.", "on", "on", ["on"], "preposition"),
    ("She sat between her two best friends during the ceremony.", "between", "between", ["between"], "preposition"),
    ("I like both coffee and tea, but I prefer coffee in the morning.", "and", "and", ["and"], "conjunction"),
    ("He is extremely tired because he worked until midnight last night.", "because", "because", ["because"], "conjunction"),
    ("I will definitely go if you promise to come with me.", "if", "if", ["if"], "conjunction"),
    ("Although it was raining heavily, they decided to continue the outdoor event.", "Although", "although", ["Although"], "conjunction"),
    ("She studied hard, yet she still failed the exam.", "yet", "yet", ["yet"], "conjunction"),
]
