db.createCollection('data-chunks');
newCol = db.getCollection('data-chunks');
newCol.createIndex({ dataId: -1 }, { name: "data-id-index" });