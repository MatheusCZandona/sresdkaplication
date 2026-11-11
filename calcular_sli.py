import urllib.request

from prometheus_client.parser import text_string_to_metric_families

URL = "http://localhost:5000/metrics"
SLO = 0.99  # meta: 99% das requisições sem erro do servidor


def ler_contagens():
    texto = urllib.request.urlopen(URL).read().decode()
    total = 0
    erros = 0
    for familia in text_string_to_metric_families(texto):
        for amostra in familia.samples:
            if amostra.name != "http_requisicoes_total":
                continue
            if amostra.labels["rota"] == "/metrics":
                continue  # não conta as consultas ao próprio placar
            total += amostra.value
            if amostra.labels["status"].startswith("5"):
                erros += amostra.value
    return total, erros


total, erros = ler_contagens()

if total == 0:
    print("Ainda não há requisições para medir.")
else:
    sli = (total - erros) / total
    orcamento = 1 - SLO
    consumido = (erros / total) / orcamento

    print(f"Total de requisições: {int(total)} | Erros 5xx: {int(erros)}")
    print(f"SLI (disponibilidade): {sli:.2%}")
    print(f"SLO (meta): {SLO:.2%}")
    print(f"Orçamento de erro consumido: {consumido:.0%}")
    print("Dentro da meta" if sli >= SLO else "META VIOLADA")