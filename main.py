import scrapy
import re


class PokeSpider(scrapy.Spider):
    name = "pokespider"
    allowed_domains = ["pokemondb.net"]
    start_urls = ["https://pokemondb.net/pokedex/all"]

    custom_settings = {
        "USER_AGENT": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.5,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "DOWNLOAD_DELAY": 0.25,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "RETRY_TIMES": 3,
    }

    def parse(self, response):
        for row in response.css("table#pokedex tbody tr"):
            href = row.css("td.cell-name a.ent-name::attr(href)").get()
            form_hint = (row.css("td.cell-name small.text-muted::text").get() or "Base").strip()
            if href:
                yield response.follow(
                    href,
                    callback=self.parse_pokemon,
                    cb_kwargs={"form_hint": form_hint},
                    dont_filter=True, 
                )

    def parse_pokemon(self, response, form_hint):
        url_pokemon = response.url
        nome = (response.css("h1::text").get() or "").strip()

        pokedex_tables = response.xpath(
            "//table[contains(@class,'vitals-table')][.//tr[th[contains(normalize-space(),'National')]]]"
        )

        table = None
        for t in pokedex_tables:
            small = t.xpath("normalize-space(preceding-sibling::h2[1]//small/text())").get()
            h2txt = t.xpath("normalize-space(preceding-sibling::h2[1]/text())").get()
            label = (small or h2txt or "").strip()
            if self._match_form(label, form_hint):
                table = t
                break
        if table is None and pokedex_tables:
            table = pokedex_tables[0]

        if table is not None:
            num_nat = table.xpath(
                ".//tr[th[contains(normalize-space(),'National')]]/td//strong/text()"
            ).get()
            num_nat = (num_nat or "").strip()

            tamanho = (table.xpath(".//tr[th[normalize-space()='Height']]/td/text()").get() or "").strip()
            peso    = (table.xpath(".//tr[th[normalize-space()='Weight']]/td/text()").get() or "").strip()

            tipos_list = table.xpath(".//tr[th[normalize-space()='Type']]/td//a/text()").getall()
            tipos = ", ".join([t.strip() for t in tipos_list])
        else:
            num_nat, tamanho, peso, tipos = "", "", "", ""

        efetividade = self._extract_effectiveness(response)

        proximas_evolucoes = self._next_evolutions(response, nome)

        hab_nomes = table.xpath(".//tr[th[normalize-space()='Abilities']]/td//a/text()").getall() if table is not None else []
        hab_urls = [response.urljoin(u) for u in table.xpath(
            ".//tr[th[normalize-space()='Abilities']]/td//a/@href"
        ).getall()] if table is not None else []

        item = {
            "numero": num_nat,
            "url": url_pokemon,
            "nome": nome,
            "proximas_evolucoes": proximas_evolucoes,
            "tamanho": tamanho,
            "peso": peso,
            "tipos": tipos,
            "efetividade": efetividade,
            "habilidades": [],
        }

        if not hab_urls:
            yield item
            return

        item["_pending"] = len(hab_urls)
        for n, u in zip(hab_nomes, hab_urls):
            yield scrapy.Request(
                u,
                callback=self.parse_ability,
                errback=self.parse_ability_error,
                cb_kwargs={"item": item, "hab_nome": n},
                dont_filter=True,
            )

    def parse_ability(self, response, item, hab_nome):
        descricao = self._extract_ability_description(response)
        item["habilidades"].append({
            "url": response.url,
            "nome": (hab_nome or "").strip(),
            "descricao": descricao,
        })

        item["_pending"] -= 1
        if item["_pending"] == 0:
            item.pop("_pending", None)
            yield item

    def parse_ability_error(self, failure):
        req = failure.request
        item = req.cb_kwargs["item"]
        hab_nome = req.cb_kwargs.get("hab_nome", "")

        item["habilidades"].append({
            "url": req.url,
            "nome": (hab_nome or "").strip(),
            "descricao": "Falha ao obter descrição",
        })

        item["_pending"] -= 1
        if item["_pending"] == 0:
            item.pop("_pending", None)
            yield item

    @staticmethod
    def _match_form(label, form_hint):
        """Compara 'Attack Forme' vs 'Attack Form', ignora caixa/hífens."""
        def norm(s):
            return (s or "").lower().replace("forme", "form").replace("-", " ").strip()
        L, F = norm(label), norm(form_hint)
        if F in ("", "base"):
            return L in ("", "base", "pokédex data")
        return F in L or L in F

    def _next_evolutions(self, response, nome_atual):
        """Retorna evoluções após o Pokémon atual."""
        cards = response.css("div.infocard-list-evo > *")
        seq = []
        for i in range(0, len(cards), 2):
            card = cards[i]
            arrow = cards[i + 1] if i + 1 < len(cards) else None

            nome = card.css("a.ent-name::text").get()
            url  = card.css("a.ent-name::attr(href)").get()
            num  = card.css("small::text").get()
            tipos = card.css("small a.itype::text").getall()

            step = {
                "numero": num,
                "nome": nome,
                "url": response.urljoin(url) if url else None,
                "tipos": tipos,
                "level_item": None,
            }
            if arrow is not None:
                txt = arrow.css("small::text").get()
                if txt:
                    step["level_item"] = txt.strip("()")
            seq.append(step)

        idx = None
        for i, s in enumerate(seq):
            if s["nome"] and nome_atual and s["nome"].strip().lower() == nome_atual.strip().lower():
                idx = i
                break
        if idx is None:
            return []

        proximos = []
        for j in range(idx + 1, len(seq)):
            s = seq[j]
            proximos.append({
                "numero": s["numero"],
                "level": s["level_item"],
                "item": None,
                "nome": s["nome"],
                "url": s["url"],
            })
        return proximos

    def _extract_effectiveness(self, response):
        table = self._find_effectiveness_table(response)
        if not table:
            return {}

        headers = table.xpath(".//thead//th[not(contains(@class,'cell-total'))]")
        if not headers:
            headers = table.xpath(".//tr[1]/th[not(contains(@class,'cell-total'))]")

        tipos = []
        for th in headers:
            t = th.xpath("normalize-space(a/text())").get()
            if not t:
                t = th.xpath("normalize-space(a/@title)").get()
            if not t:
                t = th.xpath("normalize-space(img/@alt)").get()
            if t:
                t = t.replace(" type", "").strip()
            if t:
                tipos.append(t)

        cells = table.xpath(".//tbody/tr[1]/td")
        if not cells:
            cells = table.xpath(".//tr[position()=2]/td")

        efetividade = {}
        for i, tipo in enumerate(tipos):
            if i >= len(cells):
                break
            val = (cells[i].xpath("normalize-space(text())").get() or "").strip()
            efetividade[tipo] = val if val else "1"
        return efetividade

    def _find_effectiveness_table(self, response):
        cand = response.xpath("//table[contains(@class,'type-table-pokedex')]")
        if cand:
            return cand[0]
        cand = response.xpath(
            "(//h2[contains(.,'Type defenses') or contains(.,'Damage taken')]/following-sibling::div//table"
            "[contains(@class,'type-table')])[1]"
        )
        if cand:
            return cand[0]
        cand = response.xpath("(//table[contains(@class,'type-table')])[1]")
        return cand[0] if cand else None

    def _extract_ability_description(self, response) -> str:
        """
        Prioriza a seção 'Effect' (um ou mais <p> até o próximo <h2>).
        Fallback: primeiro <p> do conteúdo.
        Fallback2: primeira célula da tabela 'Game descriptions'.
        """
        effect_ps = response.xpath(
            "//h2[normalize-space()='Effect']/"
            "following-sibling::*[preceding-sibling::h2[1][normalize-space()='Effect'] "
            "and self::p]"
        )
        if effect_ps:
            texts = []
            for p in effect_ps:
                texts.extend(p.xpath(".//text()").getall())
            desc = self._clean_text(" ".join(texts))
            if desc:
                return desc

        effect_first_p = response.xpath(
            "(//h2[normalize-space()='Effect']/following-sibling::p)[1]//text()"
        ).getall()
        desc = self._clean_text(" ".join(effect_first_p))
        if desc:
            return desc

        first_p = response.xpath("(//article//p|//main//p|//div[@id='main']//p)[1]//text()").getall()
        desc = self._clean_text(" ".join(first_p))
        if desc:
            return desc

        game_td = response.xpath(
            "(//h2[contains(.,'Game descriptions')]/following-sibling::*//table"
            "[contains(@class,'vitals-table')]//tr[1]/td)[1]//text()"
        ).getall()
        desc = self._clean_text(" ".join(game_td))
        return desc if desc else "Descrição não encontrada"

    @staticmethod
    def _clean_text(text: str) -> str:

        t = (text or "").replace("\xa0", " ")
        t = re.sub(r"\s+", " ", t).strip()
        return t
