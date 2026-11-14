"""Explicit additive demonstration fixtures. Never run during application startup."""
import argparse
import os
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from dotenv import load_dotenv
from sqlalchemy import select

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models import Category, Listing, Store, User


def demo_id(value):
    return uuid5(NAMESPACE_URL, f"https://demo.deloya.test/{value}")


def seed_demo():
    load_dotenv("../.env")
    load_dotenv(".env")
    password = os.environ.get("DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Defina DEMO_PASSWORD com pelo menos 12 caracteres para criar as contas demonstrativas")
    with SessionLocal() as db:
        users = {}
        for key, name, role in [("admin", "Administrador de demonstração", "admin"),
                                 ("cliente", "Cliente de demonstração", "customer"),
                                 ("vendedor1", "Vendedor Raízes (demonstração)", "vendor"),
                                 ("vendedor2", "Vendedor Makua (demonstração)", "vendor")]:
            email = f"{key}@demo.deloya.example.com"
            user = db.scalar(select(User).where(User.email == email))
            if user and not user.is_demo:
                raise SystemExit(f"Conta {email} não é demonstrativa; seed interrompido sem alterações")
            if not user:
                user = User(id=demo_id(f"users/{key}"), name=name, email=email,
                            password_hash=hash_password(password), role=role, is_demo=True)
                db.add(user)
                db.flush()
            users[key] = user
        categories = {}
        for slug, name in [("casa-lar", "Casa e lar"), ("moda-acessorios", "Moda e acessórios"),
                            ("tecnologia", "Tecnologia"), ("alimentacao", "Alimentação"), ("servicos", "Serviços")]:
            category = db.scalar(select(Category).where(Category.slug == slug))
            if not category:
                category = Category(id=demo_id(f"categories/{slug}"), slug=slug, name=name)
                db.add(category)
                db.flush()
            categories[slug] = category
        stores = {}
        for key, slug, name, description in [
            ("vendedor1", "raizes-de-nampula-demo", "Raízes de Nampula · Demonstração",
             "Loja fictícia de demonstração com artesanato, capulanas e produtos locais. Não representa um comerciante real."),
            ("vendedor2", "oficina-makua-demo", "Oficina Makua · Demonstração",
             "Loja fictícia de demonstração de tecnologia e serviços. Sem actividade comercial ou agenda real.")]:
            store = db.scalar(select(Store).where(Store.owner_id == users[key].id))
            if not store:
                store = Store(id=demo_id(f"stores/{key}"), owner_id=users[key].id, slug=slug, name=name,
                              description=description, province="Nampula", district="Cidade de Nampula",
                              address="Endereço fictício para demonstração, Nampula", phone="",
                              status="approved", is_demo=True)
                db.add(store)
                db.flush()
            stores[key] = store
        fixtures = [
            ("capulana", "vendedor1", "moda-acessorios", "product", "Capulana de padrões do Índico", "650.00", 24,
             "Capulana de algodão com padrões inspirados na costa moçambicana. Produto fictício para demonstração académica."),
            ("cesto", "vendedor1", "casa-lar", "product", "Cesto artesanal de palha", "1250.00", 12,
             "Cesto decorativo em fibra natural, com acabamento manual. Produto fictício; cores e dimensões são exemplificativas."),
            ("ceramica", "vendedor1", "casa-lar", "product", "Conjunto de cerâmica artesanal", "1800.00", 8,
             "Conjunto decorativo de cerâmica para o lar. Este anúncio serve exclusivamente para testar o marketplace."),
            ("caju", "vendedor1", "alimentacao", "product", "Castanha de caju torrada · 500 g", "450.00", 35,
             "Exemplo de produto alimentar local embalado. Dados demonstrativos, sem venda real nem informação nutricional certificada."),
            ("mochila", "vendedor1", "moda-acessorios", "product", "Mochila urbana em capulana", "1500.00", 7,
             "Mochila para o dia a dia com tecido de capulana. Produto fictício do catálogo de demonstração."),
            ("candeeiro", "vendedor1", "casa-lar", "product", "Candeeiro de mesa em fibra natural", "2400.00", 4,
             "Candeeiro decorativo com estrutura em fibra natural. Características e preço exclusivamente demonstrativos."),
            ("coluna", "vendedor2", "tecnologia", "product", "Coluna portátil Bluetooth", "2200.00", 10,
             "Coluna portátil para utilização doméstica. Não corresponde a um modelo de marca ou disponibilidade comercial real."),
            ("teclado", "vendedor2", "tecnologia", "product", "Teclado sem fios compacto", "1750.00", 15,
             "Teclado compacto para secretária. Anúncio fictício destinado a validar pesquisa, carrinho e stock."),
            ("reparacao", "vendedor2", "servicos", "service", "Diagnóstico e manutenção de computadores", "500.00", None,
             "Solicite uma avaliação técnica. A data pretendida depende de confirmação pelo vendedor; não existe agenda em tempo real."),
            ("costura", "vendedor1", "servicos", "service", "Costura e ajustes em capulana", "350.00", None,
             "Pedido demonstrativo de ajustes simples. O vendedor confirma disponibilidade antes da preparação do serviço."),
            ("fotografia", "vendedor2", "servicos", "service", "Fotografia para pequenos negócios", None, None,
             "Serviço sob consulta. Envie uma solicitação para acordar condições; o protótipo não realiza cobrança de serviços sem preço.")]
        created = 0
        for key, owner, category, kind, name, price, stock, description in fixtures:
            identifier = demo_id(f"listings/{key}")
            if db.get(Listing, identifier):
                continue
            db.add(Listing(id=identifier, store_id=stores[owner].id, category_id=categories[category].id,
                           slug=f"{key}-demo", kind=kind, name=name, description=description,
                           price=Decimal(price) if price else None, stock=stock,
                           sku=f"DEMO-{key.upper()}" if kind == "product" else None,
                           image_url=f"/demo/{key}.svg", images=[], status="published", is_demo=True,
                           service_location="Nampula · a confirmar com o vendedor" if kind == "service" else None,
                           estimated_duration="A confirmar pelo vendedor" if kind == "service" else None))
            created += 1
        db.commit()
    print(f"Seed demonstrativo concluído: {created} anúncios novos. Registos existentes preservados.")
    print("Contas: admin, cliente, vendedor1 e vendedor2 @demo.deloya.example.com. Password definida apenas em DEMO_PASSWORD.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True, help="Confirma a criação explícita de dados fictícios")
    parser.parse_args()
    seed_demo()
