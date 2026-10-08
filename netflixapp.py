import streamlit as st
import pandas as pd
import json
from google.cloud import firestore
from google.oauth2 import service_account
from sqlalchemy import text

# -----------------------------------
# Configuración visual
# -----------------------------------

st.markdown(
    """
    <style>
    .stApp {
        background-color: #FCE4EC;
    }

    .stButton > button,
    .stFormSubmitButton > button {
        background-color: #FCE4EC;
        color: #6D4058;
        border: 1px solid #D8A1B8;
        border-radius: 8px;
    }

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #F4CADD;
        color: #6D4058;
        border-color: #C77D9B;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------------------
# Conexión con Firestore
# -----------------------------------

if "firebase" in st.secrets:
    firebase_credentials = json.loads(st.secrets["firebase"]["credentials"])
    credentials = service_account.Credentials.from_service_account_info(
        firebase_credentials
    )
    db = firestore.Client(
        project=firebase_credentials["project_id"],
        credentials=credentials
    )
else:
    db = firestore.Client.from_service_account_json("keys.json")

st.title("Netflix Dashboard")


# -----------------------------------
# Función para obtener las películas
# -----------------------------------

def get_movies():
    movies_ref = db.collection("movies")
    movies = movies_ref.stream()

    data = []

    for movie in movies:
        data.append(movie.to_dict())

    return pd.DataFrame(data)


# -----------------------------------
# Obtener datos
# -----------------------------------

df_movies = get_movies()


# -----------------------------------
# Barra lateral
# -----------------------------------

st.sidebar.header("Opciones")

show_movies = st.sidebar.checkbox(
    "Mostrar todas las películas",
    value=True
)

st.sidebar.subheader("Buscar película")

search_text = st.sidebar.text_input("Escribe el título")

search_button = st.sidebar.button("Buscar")

st.sidebar.subheader("Buscar por director")

directors = sorted(df_movies["director"].dropna().unique())

selected_director = st.sidebar.selectbox(
    "Selecciona un director",
    directors
)

director_button = st.sidebar.button("Mostrar películas")

st.sidebar.subheader("Agregar nueva película")

new_name = st.sidebar.text_input("Título")
new_genre = st.sidebar.text_input("Género")
new_director = st.sidebar.text_input("Director")
new_company = st.sidebar.text_input("Compañía")

add_movie = st.sidebar.button("Agregar película")

# Libro de visitas
st.sidebar.subheader("Libro de visitas")

with st.sidebar.form("guestbook_form"):
    email = st.text_input("Correo electrónico")
    comment = st.text_area("Deja un comentario")

    submit_guest = st.form_submit_button("Enviar comentario")


if submit_guest:
    if email.strip() and comment.strip():
        conn = st.connection("postgresql", type="sql")

        try:
            with conn.session as session:
                session.execute(
                    text("""
                        INSERT INTO people (email, comment)
                        VALUES (:email, :comment)
                    """),
                    {
                        "email": email.strip(),
                        "comment": comment.strip()
                    }
                )
                session.commit()

            st.sidebar.success("¡Comentario registrado!")

        except Exception as e:
            st.sidebar.error("No se pudo guardar el comentario.")
            st.error(str(e))

    else:
        st.sidebar.warning("Completa ambos campos.")



# Mostrar comentarios del libro de visitas
if st.sidebar.button("Ver comentarios"):
    conn = st.connection("postgresql", type="sql")

    try:
        comments_df = conn.query(
            """
            SELECT email, comment
            FROM public.people
            ORDER BY email;
            """,
            ttl=0
        )

        st.sidebar.subheader("Comentarios registrados")

        if not comments_df.empty:
            for _, row in comments_df.iterrows():
                st.sidebar.write(f"**{row['email']}**")
                st.sidebar.write(row["comment"])
                st.sidebar.divider()
        else:
            st.sidebar.info("Todavía no hay comentarios registrados.")

    except Exception as e:
        st.sidebar.error("No se pudieron consultar los comentarios.")
        st.sidebar.code(str(e))


# -----------------------------------
# Catálogo de películas
# -----------------------------------

if show_movies:
    st.header("Catálogo de películas")
    st.dataframe(df_movies)


if search_button and search_text:
    results = df_movies[
        df_movies["name"].str.contains(
            search_text,
            case=False,
            na=False
        )
    ]

    st.header("Resultados de búsqueda")

    if len(results) > 0:
        st.dataframe(results)
    else:
        st.warning("No se encontraron películas.")


if director_button:
    director_results = df_movies[
        df_movies["director"] == selected_director
    ]

    st.header("Películas por director")

    st.write(
        f"Total de películas encontradas: {len(director_results)}"
    )

    st.dataframe(director_results)



if add_movie:
    if new_name and new_genre and new_director and new_company:
        new_movie = {
            "name": new_name,
            "genre": new_genre,
            "director": new_director,
            "company": new_company
        }

        db.collection("movies").document(new_name).set(new_movie)

        st.success("Película agregada correctamente")

        # Actualizar el DataFrame desde Firestore
        df_movies = get_movies()

    else:
        st.warning("Completa todos los campos")


