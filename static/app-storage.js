export function createPhotoStorage({dbName, storeName}) {
  let databasePromise = null;

  function openDatabase() {
    if (databasePromise) return databasePromise;
    if (!window.indexedDB) return Promise.reject(new Error("This browser does not support local photo storage."));
    databasePromise = new Promise((resolve, reject) => {
      const request = window.indexedDB.open(dbName, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(storeName)) {
          request.result.createObjectStore(storeName, {keyPath: "id"});
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Local photo storage could not be opened."));
    }).catch((error) => {
      databasePromise = null;
      throw error;
    });
    return databasePromise;
  }

  function request(mode, operation) {
    return openDatabase().then((database) => new Promise((resolve, reject) => {
      const transaction = database.transaction(storeName, mode);
      const request = operation(transaction.objectStore(storeName));
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error || new Error("Local photo storage failed."));
      transaction.onerror = () => reject(transaction.error || new Error("Local photo storage failed."));
    }));
  }

  return {
    putPhoto(photo, blob, detachedAt = null) {
      return request("readwrite", (store) => store.put({
        id: photo.id,
        name: photo.name,
        type: photo.type,
        size: blob.size,
        detachedAt,
        blob
      }));
    },
    getPhoto(id) {
      return request("readonly", (store) => store.get(id));
    },
    getAllPhotos() {
      return request("readonly", (store) => store.getAll());
    },
    deletePhoto(id) {
      return request("readwrite", (store) => store.delete(id));
    }
  };
}
