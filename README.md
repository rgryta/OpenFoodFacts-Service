# OpenFoodFacts Self-Hosted Service

A self-hosted product search service for [OpenFoodFacts](https://world.openfoodfacts.org) with daily delta synchronization. Built with FastAPI and PostgreSQL.

## Features

- 🔍 **Fast Search**: Fuzzy text search using PostgreSQL trigram indexes
- 📊 **4M+ Products**: Full OpenFoodFacts database with nutritional information
- 🔄 **Auto-Sync**: Daily delta updates + weekly cleanup
- 🔐 **API Key Auth**: Simple authentication via HTTP headers
- 🐳 **Docker Ready**: Deploy with docker-compose or Dockge
- 🚀 **CI/CD**: Automated Docker builds via GitHub Actions

## Quick Start

### Local Development

1. **Clone repository**:
   ```bash
   git clone https://github.com/rgryta/OpenFoodFacts-Service.git
   cd OpenFoodFacts-Service
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   nano .env  # Set POSTGRES_PASSWORD and API_KEYS
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

   **What happens on first start:**
   - Database initializes with schema
   - Updater checks if database is empty
   - If empty: automatically downloads 7GB JSONL and bootstraps (1-2 hours)
   - If populated: skips initialization and starts cron scheduler
   - JSONL file is kept in volume for future re-use (no re-download needed)

4. **Verify health**:
   ```bash
   curl -H "X-API-Key: your_api_key_here" http://localhost:8090/health
   ```

---

### Production Deployment (Dockge)

1. **Push code to trigger GitHub Actions**:
   ```bash
   git add .
   git commit -m "Deploy to production"
   git push origin main
   ```

2. **Wait for Docker images to build** (check Actions tab on GitHub)

3. **Import stack in Dockge**:
   - Use `compose.yaml` file
   - Stack name: `openfoodfacts`

4. **Configure environment in Dockge**:
   - `POSTGRES_PASSWORD`: Secure database password
   - `API_KEYS`: Comma-separated API keys
   - `IMAGE_TAG`: `latest` or specific version like `v1.0.0`

5. **Start stack**:
   - Start all services in Dockge
   - Updater automatically checks database and initializes if needed
   - Monitor logs: `docker logs -f openfoodfacts-updater`
   - First run: bootstraps automatically (1-2 hours)
   - Subsequent runs: skips initialization, starts cron scheduler

6. **Verify deployment**:
   ```bash
   curl -H "X-API-Key: your_key" http://<server-ip>:8090/health
   ```

---

## API Documentation

### Authentication

All endpoints (except `/health`) require API key authentication:

```bash
curl -H "X-API-Key: your_api_key_here" http://localhost:8090/api/v1/products/search?q=nutella
```

### Endpoints

#### Health Check
```
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "product_count": 4200000,
  "last_update": "2026-01-02T14:30:00"
}
```

---

#### Search by Barcode
```
GET /api/v1/products/barcode/{code}
```

**Example**:
```bash
curl -H "X-API-Key: your_key" http://localhost:8090/api/v1/products/barcode/3017620422003
```

**Response**:
```json
{
  "code": "3017620422003",
  "product_name": "Nutella",
  "brands": "Nutella, Ferrero",
  "quantity": "400 g",
  "nutrients": {
    "energy_kcal_100g": 539,
    "proteins_100g": 6.3,
    "carbohydrates_100g": 57.5,
    "fat_100g": 30.9,
    "sugars_100g": 56.3
  },
  "images": {
    "url": "https://images.openfoodfacts.org/...",
    "small_url": "https://images.openfoodfacts.org/..."
  }
}
```

---

#### Search by Name
```
GET /api/v1/products/search?q={query}&limit={limit}
```

**Parameters**:
- `q`: Search query (min 3 characters)
- `limit`: Max results (default 20, max 100)

**Example**:
```bash
curl -H "X-API-Key: your_key" "http://localhost:8090/api/v1/products/search?q=nutella&limit=5"
```

**Response**:
```json
{
  "query": "nutella",
  "count": 3,
  "results": [
    {
      "code": "3017620422003",
      "product_name": "Nutella",
      "brands": "Ferrero",
      "image_url": "https://...",
      "relevance_score": 0.95
    }
  ]
}
```

---

#### Trigger Manual Sync
```
POST /api/v1/admin/sync/trigger
```

**Response**:
```json
{
  "status": "accepted",
  "message": "Manual sync scheduled for next updater cycle"
}
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Docker Compose Stack                   │
│                                         │
│  ┌──────────────┐   ┌────────────────┐ │
│  │  FastAPI     │   │  PostgreSQL 16 │ │
│  │  Service     │──▶│  + JSONB       │ │
│  │  (Port 8090) │   │  + Trigram     │ │
│  └──────────────┘   └───────┬────────┘ │
│                              │          │
│  ┌──────────────────────────┴────────┐ │
│  │  Updater (Cron + Python)          │ │
│  │  - Daily delta sync (2 AM)        │ │
│  │  - Weekly cleanup (Sun 3 AM)      │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### Data Flow

1. **Initial Bootstrap**: Downloads 7GB JSONL from OpenFoodFacts → PostgreSQL (1-2 hours)
2. **Daily Updates**:
   - Checks for new delta files (14-day rolling window)
   - Applies only unapplied deltas in chronological order
   - Tracks applied deltas in `.applied_deltas.txt`
   - Downloads delta JSONL → UPSERT to PostgreSQL (~2-5 minutes per delta)
3. **Weekly Cleanup**: Compares database vs fresh Parquet → Delete obsolete products (~30 minutes)

---

## Resource Requirements

**Minimum**:
- CPU: 2 cores
- RAM: 4 GB
- Disk: 30 GB
- Network: 100 Mbps

**Recommended**:
- CPU: 4 cores
- RAM: 8 GB
- Disk: 50 GB SSD

**Database Size**: ~15-20 GB (4.2M products + indexes)

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL password |
| `API_KEYS` | Yes | - | Comma-separated API keys |
| `IMAGE_TAG` | No | `latest` | Docker image version (Dockge only) |
| `OFF_DELTA_URL` | No | OpenFoodFacts delta URL | Override delta source |
| `OFF_PARQUET_URL` | No | Hugging Face Parquet URL | Override Parquet source |

---

## Maintenance

### View Logs

**Docker Compose**:
```bash
docker-compose logs -f off-api
docker-compose logs -f off-updater
```

**Dockge**: View logs in Dockge UI

### Manual Sync

```bash
docker exec openfoodfacts-updater python /app/scripts/delta_update.py
```

### Force Re-initialization

To force a complete re-bootstrap (useful for testing):
```bash
# Stop services
docker-compose down

# Clear database
docker volume rm openfoodfacts-service_off-db-data

# Optionally clear cached JSONL to force re-download
docker volume rm openfoodfacts-service_off-data-cache

# Start again (will auto-initialize)
docker-compose up -d
```

### Database Backup

```bash
docker exec openfoodfacts-db pg_dump -U offuser openfoodfacts | gzip > backup.sql.gz
```

### Database Restore

```bash
gunzip -c backup.sql.gz | docker exec -i openfoodfacts-db psql -U offuser -d openfoodfacts
```

---

## Troubleshooting

### Issue: API returns 401 Unauthorized

**Solution**: Check `API_KEYS` environment variable matches the key in `X-API-Key` header

### Issue: Database connection failed

**Solution**:
1. Check PostgreSQL container is healthy: `docker ps`
2. Verify `POSTGRES_PASSWORD` matches in all services
3. Check logs: `docker-compose logs off-db`

### Issue: Search returns no results

**Solution**:
1. Check database has products: `curl http://localhost:8090/health`
2. Ensure bootstrap completed successfully
3. Verify trigram indexes: `docker exec openfoodfacts-db psql -U offuser -d openfoodfacts -c "\d products"`

### Issue: Initial bootstrap fails with out-of-memory

**Solution**: Increase Docker memory limit to 4GB+ in Docker settings

### Issue: Cron jobs running during bootstrap

**Solution**: Not a problem! Delta and cleanup scripts automatically check for `.bootstrap_complete` marker and skip if bootstrap hasn't finished. Once bootstrap completes, cron jobs will run normally.

### Issue: Missed delta updates for several days

**Solution**: The updater tracks which deltas have been applied in `.applied_deltas.txt`. When it runs, it processes ALL pending deltas in chronological order, catching up automatically. No manual intervention needed.

### Issue: Want to re-apply all deltas from scratch

**Solution**:
```bash
docker exec openfoodfacts-updater rm /app/data/.applied_deltas.txt
docker exec openfoodfacts-updater python /app/scripts/delta_update.py
```

---

## Development

### Project Structure

```
OpenFoodFacts-Service/
├── api/                    # FastAPI service
│   ├── app/
│   │   ├── main.py        # Application entry point
│   │   ├── routers/       # API endpoints
│   │   ├── middleware/    # Auth middleware
│   │   └── models.py      # Pydantic models
│   └── Dockerfile
├── updater/               # Data sync service
│   ├── scripts/
│   │   ├── initial_load.py
│   │   ├── delta_update.py
│   │   └── weekly_cleanup.py
│   └── Dockerfile
├── db/                    # Database schema
│   ├── init.sql
│   └── extensions.sql
├── .github/workflows/     # CI/CD
└── compose.yaml           # Production stack
```

### Running Tests

```bash
cd api
pytest tests/
```

---

## License

See [LICENSE](LICENSE) file.

---

## Contributing

This is a personal project. Feel free to fork and adapt for your needs.

---

## Links

- [OpenFoodFacts](https://world.openfoodfacts.org)
- [OpenFoodFacts API Documentation](https://openfoodfacts.github.io/openfoodfacts-server/api/)
- [Hugging Face Dataset](https://huggingface.co/datasets/openfoodfacts/product-database)
