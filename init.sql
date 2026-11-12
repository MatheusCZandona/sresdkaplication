CREATE TABLE compras (
    id SERIAL PRIMARY KEY,
    item TEXT NOT NULL,
    valor DOUBLE PRECISION NOT NULL
);

INSERT INTO compras (item, valor) VALUES
    ('teclado', 150.0),
    ('mouse', 80.0);