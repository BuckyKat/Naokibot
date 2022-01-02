import os

async def scry(path, results=[]):
    tree = []
    async def helper():
        for filename in os.listdir(path):
            if 'posts' not in filename and '.' not in filename:
                return await scry(path+'/'+filename, results)
            else:
                results.append(filename)
    helper()

    return results
    