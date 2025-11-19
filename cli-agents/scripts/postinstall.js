#!/usr/bin/env node

/**
 * Post-install script for CLI agents
 * Builds and installs Node.js CLI agents to the .venv
 */

import { execSync } from 'child_process';
import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

const cliAgentsDir = process.cwd();
const rootDir = join(cliAgentsDir, '..');
const venvDir = join(rootDir, '.venv');

function buildAndInstallAgents() {
  console.log('Building and installing CLI agents...');
  
  try {
    // First, build Qwen if the source exists
    const qwenDir = join(cliAgentsDir, 'qwen-code');
    if (existsSync(qwenDir)) {
      console.log('Building Qwen CLI from source...');
      execSync('npm run build', { 
        cwd: qwenDir, 
        stdio: 'inherit' 
      });
      console.log('Qwen CLI built successfully');
    } else {
      console.log('Qwen source directory not found, skipping build');
    }

    // Install all agents using npm
    console.log('Installing CLI agents to venv...');
    execSync('npm install --global', { 
      cwd: cliAgentsDir,
      stdio: 'inherit',
      env: {
        ...process.env,
        // Point to the venv's npm
        PATH: `${join(venvDir, 'bin')}:${process.env.PATH}`
      }
    });
    
    console.log('CLI agents installed successfully');
  } catch (error) {
    console.error('Failed to build/install CLI agents:', error.message);
    process.exit(1);
  }
}

if (require.main === module) {
  buildAndInstallAgents();
}