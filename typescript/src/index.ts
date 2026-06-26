#!/usr/bin/env node
/**
 * Loop Engineering MCP Server - TypeScript Implementation
 * Entry point
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { createServer } from './server.js';

async function main() {
  try {
    const { server, scheduler } = createServer();
    if (scheduler) scheduler.start();

    const transport = new StdioServerTransport();
    await server.connect(transport);

    process.on('SIGINT', async () => {
      console.error('\nShutting down Loop Engineering MCP server...');
      if (scheduler) await scheduler.stop();
      await server.close();
      process.exit(0);
    });
  } catch (error) {
    console.error('Error running server:', error);
    process.exit(1);
  }
}

main();
