example_instructions ="""
To correct the issue related to the `createEmitter` method, we need to change how the particles are added and configure the emitter accordingly. The error message indicates that `createEmitter` has been removed and replaced within the ParticleEmitter configuration in recent versions of Phaser.

Here's the search and replace edit required to fix the issue:

```javascript
<<<<<<< SEARCH
        this.emitter = this.add.particles('pixel').createEmitter({
            speed: 200,
            scale: { start: 1, end: 0 },
            blendMode: 'ADD'
        });
=======
        this.particles = this.add.particles('pixel'); // modify successfully
        this.emitter = this.particles.createEmitter({
            speed: 200,
            scale: { start: 1, end: 0 },
            blendMode: 'ADD'
        });
>>>>>>> REPLACE
<<<<<<< SEARCH
        let particles;
=======
        let particles = 0; // modify successfully
>>>>>>> REPLACE
```
Also
```javascript
<<<<<<< SEARCH
    a += 1;
=======
    a += 2; // modify successfully
>>>>>>> REPLACE
```
This modification ensures particles are correctly added and an emitter is created using the updated Phaser API.
"""

example_code = """
    a += 1;
    let particles;
        this.emitter = this.add.particles('pixel').createEmitter({
            speed: 200,
            scale: { start: 1, end: 0 },
            blendMode: 'ADD'
        });
"""

# incorrect indentation in the code
example_code2 = """
        a += 1;
        let particles;
            this.emitter = this.add.particles('pixel').createEmitter({
                speed: 200,
                scale: { start: 1, end: 0 },
                blendMode: 'ADD'
            });
"""

# extra whitespace in the code
example_code3 = """
a += 1;
let particles;
    this.emitter = this.add.particles('pixel').createEmitter({
        speed: 200,
        scale: { start: 1, end: 0 },
        blendMode: 'ADD' 
    });  
"""

