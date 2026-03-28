class RouletteSpinSchema:

    @staticmethod
    def create_table() -> str:
        return """
            CREATE TABLE IF NOT EXISTS roulette_spins (
                id VARCHAR(255) PRIMARY KEY,
                created_at TIMESTAMP NOT NULL,
                color INTEGER NOT NULL,
                roll INTEGER NOT NULL
            )
        """

    @staticmethod
    def insert() -> str:
        return """
            INSERT INTO roulette_spins (id, created_at, color, roll)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
        """

    @staticmethod
    def exists() -> str:
        return """
            SELECT 1 FROM roulette_spins WHERE id = %s
        """
