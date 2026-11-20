import streamlit as st
import pandas as pd
import json
import os
from itertools import combinations

# Configuração da página
st.set_page_config(page_title="FutPorto — Gestor de Torneio", page_icon="⚽", layout="wide")

FICHEIRO_DADOS = "futporto_dados.json"

REGULAMENTO_PADRAO = """### 📜 Regulamento Oficial — FutPorto

1. **Formato da Competição:**
   - Fase de Liga em sistema de todos contra todos (3 pontos por vitória, 1 por empate, 0 por derrota).
   - **Com 4 equipas:** Os 2 primeiros disputam a **Grande Final** e o 3º e 4º disputam o **3º/4º Lugar**.
   - **Com 3 equipas:** Os 2 primeiros disputam a **Grande Final** e o 3º lugar fica atribuído pela tabela da liga.

2. **Critérios de Desempate na Liga:**
   - 1.º Maior número de pontos
   - 2.º Diferença de golos (GM - GS)
   - 3.º Maior número de golos marcados

3. **Finais:**
   - Em caso de empate no tempo regulamentar, a decisão segue para grandes penalidades (ajusta o resultado final no marcador).

4. **Prémios Individuais e Coletivos:**
   - **MVP**, **Bola de Ouro**, **Chuteira de Ouro**, **Luva de Ouro**, **Melhor Defesa** e **Puskás**.
"""

# --- GESTÃO DE DADOS (GUARDAR / CARREGAR) ---
def carregar_dados():
    if os.path.exists(FICHEIRO_DADOS):
        with open(FICHEIRO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
    else:
        dados = {}

    # Garante compatibilidade e chaves completas
    dados.setdefault("num_equipas", 4)
    dados.setdefault("equipas", [])
    dados.setdefault("jogos_liga", [])
    dados.setdefault("finais", {
        "final": {"casa": "", "fora": "", "golos_casa": 0, "golos_fora": 0, "jogado": False},
        "terceiro": {"casa": "", "fora": "", "golos_casa": 0, "golos_fora": 0, "jogado": False}
    })
    dados.setdefault("eventos", [])
    dados.setdefault("regulamento", REGULAMENTO_PADRAO)
    dados.setdefault("notas_premios", "")
    dados.setdefault("premios", {
        "mvp": "",
        "bola_ouro": "",
        "chuteira_ouro": "",
        "luva_ouro": "",
        "melhor_defesa": "",
        "puskas": ""
    })
    return dados

def guardar_dados(dados):
    with open(FICHEIRO_DADOS, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

dados = carregar_dados()

# --- CÁLCULO DA CLASSIFICAÇÃO ---
def calcular_classificacao():
    tabela = {
        eq: {"Equipa": eq, "J": 0, "V": 0, "E": 0, "D": 0, "GM": 0, "GS": 0, "DG": 0, "Pts": 0}
        for eq in dados["equipas"]
    }

    for jogo in dados["jogos_liga"]:
        if jogo["jogado"]:
            c, f = jogo["casa"], jogo["fora"]
            gc, gf = jogo["golos_casa"], jogo["golos_fora"]

            tabela[c]["J"] += 1
            tabela[f]["J"] += 1
            tabela[c]["GM"] += gc
            tabela[c]["GS"] += gf
            tabela[f]["GM"] += gf
            tabela[f]["GS"] += gc

            if gc > gf:
                tabela[c]["V"] += 1
                tabela[c]["Pts"] += 3
                tabela[f]["D"] += 1
            elif gf > gc:
                tabela[f]["V"] += 1
                tabela[f]["Pts"] += 3
                tabela[c]["D"] += 1
            else:
                tabela[c]["E"] += 1
                tabela[f]["E"] += 1
                tabela[c]["Pts"] += 1
                tabela[f]["Pts"] += 1

    for eq in tabela:
        tabela[eq]["DG"] = tabela[eq]["GM"] - tabela[eq]["GS"]

    df = pd.DataFrame(list(tabela.values()))
    if not df.empty:
        df = df.sort_values(by=["Pts", "DG", "GM"], ascending=[False, False, False]).reset_index(drop=True)
        df.index += 1
    return df

# --- CABEÇALHO E BARRA LATERAL ---
st.title("⚽ FutPorto — Gestor de Torneio")

with st.sidebar:
    st.markdown("### 🏟️ FutPorto")
    if dados["equipas"]:
        st.caption(f"Formato ativo: **{len(dados['equipas'])} equipas** ({len(dados['jogos_liga'])} jogos na liga)")
    st.divider()
    if st.button("🗑️ Reiniciar Torneio Completo", type="secondary", use_container_width=True):
        if os.path.exists(FICHEIRO_DADOS):
            os.remove(FICHEIRO_DADOS)
        st.rerun()

# --- SEPARADORES ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "1️⃣ Equipas",
    "2️⃣ Liga & Classificação",
    "3️⃣ Eventos",
    "4️⃣ Finais",
    "🏆 Prémios & Apontamentos",
    "📜 Regulamento"
])

# ==========================================
# TAB 1: CONFIGURAÇÃO (3 OU 4 EQUIPAS)
# ==========================================
with tab1:
    st.subheader("Configuração do Torneio FutPorto")

    if len(dados["equipas"]) in (3, 4):
        st.success(f"Torneio configurado com **{len(dados['equipas'])} equipas**: **{', '.join(dados['equipas'])}**")
        st.info("Para alterar o número ou os nomes das equipas, reinicia o torneio na barra lateral.")
    else:
        qtd = st.radio(
            "Quantas equipas vão participar neste FutPorto?",
            options=[4, 3],
            format_func=lambda x: f"{x} equipas ({'6 jogos na liga + Final e 3º/4º lugar' if x == 4 else '3 jogos na liga + Final'})",
            horizontal=True
        )

        with st.form("form_equipas"):
            cols = st.columns(2)
            inputs = []
            for i in range(qtd):
                col = cols[i % 2]
                inputs.append(col.text_input(f"Equipa {i + 1}"))

            if st.form_submit_button("Criar Torneio e Gerar Jogos"):
                equipas = [e.strip() for e in inputs if e.strip()]
                if len(equipas) == qtd and len(set(equipas)) == qtd:
                    dados["num_equipas"] = qtd
                    dados["equipas"] = equipas
                    dados["finais"] = {
                        "final": {"casa": "", "fora": "", "golos_casa": 0, "golos_fora": 0, "jogado": False},
                        "terceiro": {"casa": "", "fora": "", "golos_casa": 0, "golos_fora": 0, "jogado": False}
                    }
                    jogos = []
                    for idx_j, (c, f) in enumerate(combinations(equipas, 2), 1):
                        jogos.append({
                            "id": idx_j,
                            "casa": c,
                            "fora": f,
                            "golos_casa": 0,
                            "golos_fora": 0,
                            "jogado": False
                        })
                    dados["jogos_liga"] = jogos
                    guardar_dados(dados)
                    st.rerun()
                else:
                    st.error(f"Preenche exatamente {qtd} equipas com nomes diferentes.")

# ==========================================
# TAB 2: JOGOS DA LIGA E CLASSIFICAÇÃO
# ==========================================
with tab2:
    if len(dados["equipas"]) < 3:
        st.warning("Configura primeiro as equipas no separador **1️⃣ Equipas**.")
    else:
        col_jogos, col_tab = st.columns([1.2, 1])

        with col_jogos:
            st.subheader("📅 Jogos da Fase de Liga")
            for idx, jogo in enumerate(dados["jogos_liga"]):
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2.2, 1, 0.5, 1, 2.2])
                    c1.markdown(f"**{jogo['casa']}**")
                    gc = c2.number_input("GC", min_value=0, value=jogo["golos_casa"], key=f"gc_{idx}", label_visibility="collapsed")
                    c3.markdown("<div style='text-align: center; padding-top: 5px;'>vs</div>", unsafe_allow_html=True)
                    gf = c4.number_input("GF", min_value=0, value=jogo["golos_fora"], key=f"gf_{idx}", label_visibility="collapsed")
                    c5.markdown(f"**{jogo['fora']}**")

                    jogado = st.checkbox("Jogo concluído", value=jogo["jogado"], key=f"chk_{idx}")

                    if gc != jogo["golos_casa"] or gf != jogo["golos_fora"] or jogado != jogo["jogado"]:
                        dados["jogos_liga"][idx]["golos_casa"] = gc
                        dados["jogos_liga"][idx]["golos_fora"] = gf
                        dados["jogos_liga"][idx]["jogado"] = jogado
                        guardar_dados(dados)
                        st.rerun()

        with col_tab:
            st.subheader("📊 Tabela Classificativa")
            df_class = calcular_classificacao()
            st.dataframe(df_class, use_container_width=True)
            st.caption("Critérios: Pontos (Pts) > Diferença de Golos (DG) > Golos Marcados (GM)")

# ==========================================
# TAB 3: GOLOS, ASSISTÊNCIAS E CARTÕES
# ==========================================
with tab3:
    if len(dados["equipas"]) < 3:
        st.warning("Configura primeiro as equipas no separador **1️⃣ Equipas**.")
    else:
        st.subheader("📝 Registar Evento de Jogo")

        lista_jogos = [f"Liga: {j['casa']} vs {j['fora']}" for j in dados["jogos_liga"]]
        if dados["finais"]["final"]["casa"]:
            lista_jogos.append(f"Final: {dados['finais']['final']['casa']} vs {dados['finais']['final']['fora']}")
        if dados["finais"]["terceiro"]["casa"]:
            lista_jogos.append(f"3º/4º: {dados['finais']['terceiro']['casa']} vs {dados['finais']['terceiro']['fora']}")

        with st.form("form_eventos", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns(4)
            jogo_sel = c1.selectbox("Jogo", lista_jogos)
            equipa_sel = c2.selectbox("Equipa", dados["equipas"])
            jogador = c3.text_input("Nome do Jogador")
            tipo_evento = c4.selectbox("Tipo de Registo", [
                "⚽ Golo",
                "👟 Assistência",
                "🟨 Cartão Amarelo",
                "🟥 Cartão Vermelho"
            ])

            if st.form_submit_button("Adicionar Registo"):
                if jogador.strip():
                    dados["eventos"].append({
                        "Jogo": jogo_sel,
                        "Equipa": equipa_sel,
                        "Jogador": jogador.strip().title(),
                        "Tipo": tipo_evento
                    })
                    guardar_dados(dados)
                    st.rerun()
                else:
                    st.error("Escreve o nome do jogador.")

        st.divider()

        if dados["eventos"]:
            df_ev = pd.DataFrame(dados["eventos"])
            col_g, col_a, col_c = st.columns(3)

            with col_g:
                st.markdown("#### ⚽ Melhores Marcadores")
                golos = df_ev[df_ev["Tipo"] == "⚽ Golo"].groupby(["Jogador", "Equipa"]).size().reset_index(name="Golos")
                golos = golos.sort_values(by="Golos", ascending=False).reset_index(drop=True)
                st.dataframe(golos, use_container_width=True, hide_index=True)

            with col_a:
                st.markdown("#### 👟 Assistências")
                assists = df_ev[df_ev["Tipo"] == "👟 Assistência"].groupby(["Jogador", "Equipa"]).size().reset_index(name="Assistências")
                assists = assists.sort_values(by="Assistências", ascending=False).reset_index(drop=True)
                st.dataframe(assists, use_container_width=True, hide_index=True)

            with col_c:
                st.markdown("#### 🟨🟥 Cartões")
                cartoes = df_ev[df_ev["Tipo"].isin(["🟨 Cartão Amarelo", "🟥 Cartão Vermelho"])]
                if not cartoes.empty:
                    resumo_c = cartoes.groupby(["Jogador", "Equipa", "Tipo"]).size().unstack(fill_value=0).reset_index()
                    st.dataframe(resumo_c, use_container_width=True, hide_index=True)
                else:
                    st.info("Sem cartões registados.")

            with st.expander("Ver / Apagar Histórico de Registos"):
                st.dataframe(df_ev, use_container_width=True)
                if st.button("Apagar último registo"):
                    dados["eventos"].pop()
                    guardar_dados(dados)
                    st.rerun()

# ==========================================
# TAB 4: FINAIS
# ==========================================
with tab4:
    if len(dados["equipas"]) < 3:
        st.warning("Configura primeiro as equipas no separador **1️⃣ Equipas**.")
    else:
        total_liga = len(dados["jogos_liga"])
        jogos_concluidos = sum(1 for j in dados["jogos_liga"] if j["jogado"])
        qtd_eq = len(dados["equipas"])

        st.info(f"Jogos da Liga concluídos: **{jogos_concluidos} / {total_liga}**")

        if st.button("🔄 Gerar / Atualizar Confrontos com base na Classificação"):
            df_class = calcular_classificacao()
            dados["finais"]["final"]["casa"] = df_class.loc[1, "Equipa"]
            dados["finais"]["final"]["fora"] = df_class.loc[2, "Equipa"]

            if qtd_eq == 4:
                dados["finais"]["terceiro"]["casa"] = df_class.loc[3, "Equipa"]
                dados["finais"]["terceiro"]["fora"] = df_class.loc[4, "Equipa"]
            else:
                dados["finais"]["terceiro"] = {"casa": "", "fora": "", "golos_casa": 0, "golos_fora": 0, "jogado": False}

            guardar_dados(dados)
            st.rerun()

        if qtd_eq == 3:
            df_class = calcular_classificacao()
            st.caption(f"3.º Lugar definido pela Liga: **{df_class.loc[3, 'Equipa']}**")

        if dados["finais"]["final"]["casa"]:
            if qtd_eq == 4:
                col_f, col_t = st.columns(2)
            else:
                col_f = st.container()
                col_t = None

            with col_f:
                st.markdown("### 🏆 Grande Final (1º vs 2º)")
                fin = dados["finais"]["final"]
                with st.container(border=True):
                    c1, c2, c3, c4, c5 = st.columns([2.2, 1, 0.5, 1, 2.2])
                    c1.markdown(f"**{fin['casa']}**")
                    fgc = c2.number_input("FGC", min_value=0, value=fin["golos_casa"], label_visibility="collapsed")
                    c3.markdown("<div style='text-align: center; padding-top: 5px;'>vs</div>", unsafe_allow_html=True)
                    fgf = c4.number_input("FGF", min_value=0, value=fin["golos_fora"], label_visibility="collapsed")
                    c5.markdown(f"**{fin['fora']}**")
                    f_jogado = st.checkbox("Final concluída", value=fin["jogado"])

                    if fgc != fin["golos_casa"] or fgf != fin["golos_fora"] or f_jogado != fin["jogado"]:
                        dados["finais"]["final"]["golos_casa"] = fgc
                        dados["finais"]["final"]["golos_fora"] = fgf
                        dados["finais"]["final"]["jogado"] = f_jogado
                        guardar_dados(dados)
                        st.rerun()

                    if f_jogado:
                        if fgc > fgf:
                            st.success(f"🥇 CAMPEÃO FUTPORTO: **{fin['casa']}** | 🥈 2º Lugar: **{fin['fora']}**")
                        elif fgf > fgc:
                            st.success(f"🥇 CAMPEÃO FUTPORTO: **{fin['fora']}** | 🥈 2º Lugar: **{fin['casa']}**")
                        else:
                            st.warning("Empate! Decide nos penáltis e ajusta o marcador acima.")

            if col_t is not None and dados["finais"]["terceiro"]["casa"]:
                with col_t:
                    st.markdown("### 🥉 Disputa 3º e 4º Lugar (3º vs 4º)")
                    ter = dados["finais"]["terceiro"]
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns([2.2, 1, 0.5, 1, 2.2])
                        c1.markdown(f"**{ter['casa']}**")
                        tgc = c2.number_input("TGC", min_value=0, value=ter["golos_casa"], label_visibility="collapsed")
                        c3.markdown("<div style='text-align: center; padding-top: 5px;'>vs</div>", unsafe_allow_html=True)
                        tgf = c4.number_input("TGF", min_value=0, value=ter["golos_fora"], label_visibility="collapsed")
                        c5.markdown(f"**{ter['fora']}**")
                        t_jogado = st.checkbox("Jogo 3º/4º concluído", value=ter["jogado"])

                        if tgc != ter["golos_casa"] or tgf != ter["golos_fora"] or t_jogado != ter["jogado"]:
                            dados["finais"]["terceiro"]["golos_casa"] = tgc
                            dados["finais"]["terceiro"]["golos_fora"] = tgf
                            dados["finais"]["terceiro"]["jogado"] = t_jogado
                            guardar_dados(dados)
                            st.rerun()

                        if t_jogado:
                            if tgc > tgf:
                                st.info(f"🥉 3º Lugar: **{ter['casa']}** | 4º Lugar: **{ter['fora']}**")
                            elif tgf > tgc:
                                st.info(f"🥉 3º Lugar: **{ter['fora']}** | 4º Lugar: **{ter['casa']}**")
                            else:
                                st.warning("Empate! Decide nos penáltis e ajusta o marcador acima.")

# ==========================================
# TAB 5: PRÉMIOS FUTPORTO & APONTAMENTOS
# ==========================================
with tab5:
    st.subheader("🏆 Prémios Oficiais FutPorto")

    # Referências automáticas a partir dos dados registados
    sug_chuteira = "Sem golos registados"
    sug_luva = "Sem jogos concluídos"

    if dados["eventos"]:
        df_ev = pd.DataFrame(dados["eventos"])
        g = df_ev[df_ev["Tipo"] == "⚽ Golo"].groupby(["Jogador", "Equipa"]).size().sort_values(ascending=False)
        if not g.empty:
            jogador_top, equipa_top = g.index[0]
            sug_chuteira = f"{jogador_top} ({equipa_top}) — {g.iloc[0]} golos"

    df_class = calcular_classificacao()
    if not df_class.empty and df_class["J"].sum() > 0:
        menos_sofridos = df_class.sort_values(by=["GS", "DG"], ascending=[True, False]).iloc[0]
        sug_luva = f"{menos_sofridos['Equipa']} ({menos_sofridos['GS']} GS)"

    c_ref1, c_ref2 = st.columns(2)
    c_ref1.metric("👟 Referência Chuteira de Ouro (Golos)", sug_chuteira)
    c_ref2.metric("🧤 Referência Luva de Ouro (Menos GS)", sug_luva)

    st.divider()

    col_p, col_n = st.columns([1.15, 1])

    with col_p:
        st.markdown("#### 🎖️ Atribuição dos 6 Prémios")
        with st.form("form_premios_futporto"):
            mvp = st.text_input("🌟 MVP", value=dados["premios"].get("mvp", ""), placeholder="Jogador mais valioso do torneio")
            bola_ouro = st.text_input("🥇 Bola de Ouro", value=dados["premios"].get("bola_ouro", ""), placeholder="Melhor jogador / destaque")
            chuteira_ouro = st.text_input("👟 Chuteira de Ouro", value=dados["premios"].get("chuteira_ouro", ""), placeholder="Melhor marcador")
            luva_ouro = st.text_input("🧤 Luva de Ouro", value=dados["premios"].get("luva_ouro", ""), placeholder="Melhor guarda-redes")
            melhor_defesa = st.text_input("🛡️ Melhor Defesa", value=dados["premios"].get("melhor_defesa", ""), placeholder="Jogador ou defesa em destaque")
            puskas = st.text_input("🔥 Prémio Puskás", value=dados["premios"].get("puskas", ""), placeholder="Golo mais bonito do torneio")

            if st.form_submit_button("Guardar Prémios FutPorto", use_container_width=True):
                dados["premios"] = {
                    "mvp": mvp.strip(),
                    "bola_ouro": bola_ouro.strip(),
                    "chuteira_ouro": chuteira_ouro.strip(),
                    "luva_ouro": luva_ouro.strip(),
                    "melhor_defesa": melhor_defesa.strip(),
                    "puskas": puskas.strip()
                }
                guardar_dados(dados)
                st.success("Prémios guardados com sucesso!")

    with col_n:
        st.markdown("#### 📓 Apontamentos para Atribuir Prémios")
        st.caption("Usa este espaço para anotar candidatos, lances de Puskás, defesas decisivas ou momentos de destaque durante os jogos.")
        with st.form("form_notas_premios"):
            notas = st.text_area(
                "Bloco de notas dos prémios",
                value=dados.get("notas_premios", ""),
                height=310,
                placeholder="Ex.:\n- Puskás: bicicleta do João no jogo 2\n- Luva de Ouro: 3 defesas na cara do golo pelo guarda-redes da Equipa B\n- Melhor Defesa: cortes limpos do Pedro na final..."
            )
            if st.form_submit_button("Guardar Apontamentos", use_container_width=True):
                dados["notas_premios"] = notas
                guardar_dados(dados)
                st.success("Apontamentos guardados!")

# ==========================================
# TAB 6: REGULAMENTO DO TORNEIO
# ==========================================
with tab6:
    st.subheader("📜 Regulamento do FutPorto")

    col_reg_view, col_reg_edit = st.columns([1, 1])

    with col_reg_view:
        st.markdown("#### Pré-visualização do Regulamento")
        with st.container(border=True):
            st.markdown(dados.get("regulamento", REGULAMENTO_PADRAO))

    with col_reg_edit:
        st.markdown("#### Editar / Colar Regulamento")
        with st.form("form_regulamento"):
            novo_reg = st.text_area(
                "Texto do regulamento (suporta Markdown)",
                value=dados.get("regulamento", REGULAMENTO_PADRAO),
                height=380
            )
            if st.form_submit_button("Guardar Regulamento", use_container_width=True):
                dados["regulamento"] = novo_reg
                guardar_dados(dados)
                st.success("Regulamento atualizado com sucesso!")
                st.rerun()
