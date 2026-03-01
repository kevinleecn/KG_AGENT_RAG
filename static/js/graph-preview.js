/**
 * Graph Preview Component for Knowledge Graph Nodes card
 * Reuses D3.js logic from graph.html
 * Provides interactive force-directed graph visualization
 */
class GraphPreview {
    /**
     * Create a GraphPreview instance
     * @param {string} containerId - ID of the container element
     * @param {object} options - Configuration options
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container with ID "${containerId}" not found`);
        }

        this.options = {
            width: this.container.clientWidth,
            height: this.container.clientHeight,
            maxNodes: 50,          // Limit nodes for performance
            nodeRadius: 8,
            linkDistance: 100,
            chargeStrength: -300,
            collisionRadius: 30,
            showLabels: true,
            colorScheme: 'categorical', // 'categorical', 'set3', 'pastel1'
            ...options
        };

        // Internal state
        this.svg = null;
        this.simulation = null;
        this.zoom = null;
        this.g = null;
        this.nodes = [];
        this.links = [];
        this.nodeColorScale = null;
        this.linkColorScale = null;
        this.nodeElements = null;
        this.linkElements = null;
        this.nodeLabelElements = null;
        this.linkLabelElements = null;

        // Color schemes (matching graph.html)
        this.colorSchemes = {
            categorical: d3.scaleOrdinal(d3.schemeCategory10),
            set3: d3.scaleOrdinal(d3.schemeSet3),
            pastel1: d3.scaleOrdinal(d3.schemePastel1)
        };

        this.init();
    }

    /**
     * Initialize the graph container
     */
    init() {
        // Clear container
        d3.select(this.container).selectAll('*').remove();

        // Create SVG
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', this.options.width)
            .attr('height', this.options.height)
            .attr('class', 'graph-svg');

        // Set up zoom behavior
        this.setupZoom();

        // Create arrow marker for directed links
        this.createArrowMarker();

        // Create main group for zoom
        this.g = this.svg.append('g');

        // Create tooltip element
        this.createTooltip();
    }

    /**
     * Set up zoom and pan behavior
     */
    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.g.attr('transform', event.transform);
            });

        this.svg.call(this.zoom);
    }

    /**
     * Create arrow marker for directed links
     */
    createArrowMarker() {
        this.svg.append('defs').append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 12)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M0,-5L10,0L0,5')
            .attr('fill', '#999');
    }

    /**
     * Create tooltip element
     */
    createTooltip() {
        // Tooltip is already in HTML, just get reference
        this.tooltip = d3.select('#graphTooltip');
    }

    /**
     * Render graph data
     * @param {object} data - Graph data with nodes and links
     */
    render(data) {
        if (!data || !data.nodes || !data.links) {
            this.showEmptyState();
            return;
        }

        // Limit nodes for performance
        const displayNodes = data.nodes.slice(0, this.options.maxNodes);
        const displayLinks = data.links.filter(link =>
            displayNodes.some(n => n.id === link.source) &&
            displayNodes.some(n => n.id === link.target)
        );

        this.nodes = displayNodes.map(d => ({ ...d }));
        this.links = displayLinks.map(d => ({
            ...d,
            source: this.nodes.find(n => n.id === d.source) || d.source,
            target: this.nodes.find(n => n.id === d.target) || d.target
        }));

        // Create color scales
        this.createColorScales();

        // Clear previous graph
        this.g.selectAll('*').remove();

        // Create force simulation
        this.createSimulation();

        // Create visual elements
        this.createLinks();
        this.createLinkLabels();
        this.createNodes();
        this.createNodeLabels();

        // Start simulation
        this.simulation.alpha(1).restart();

        // Update legend
        this.updateLegend();
    }

    /**
     * Create color scales for nodes and links
     */
    createColorScales() {
        const entityTypes = [...new Set(this.nodes.map(d => d.type))];
        this.nodeColorScale = this.colorSchemes[this.options.colorScheme]
            .domain(entityTypes)
            .copy();

        const relationshipTypes = [...new Set(this.links.map(d => d.type))];
        this.linkColorScale = this.colorSchemes.set3
            .domain(relationshipTypes)
            .copy();
    }

    /**
     * Create force simulation
     */
    createSimulation() {
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.links)
                .id(d => d.id)
                .distance(this.options.linkDistance))
            .force('charge', d3.forceManyBody()
                .strength(this.options.chargeStrength))
            .force('center', d3.forceCenter(
                this.options.width / 2,
                this.options.height / 2))
            .force('collision', d3.forceCollide()
                .radius(this.options.collisionRadius))
            .on('tick', () => this.ticked());
    }

    /**
     * Create link elements
     */
    createLinks() {
        this.linkElements = this.g.append('g')
            .attr('class', 'graph-links')
            .selectAll('line')
            .data(this.links)
            .enter()
            .append('line')
            .attr('class', 'graph-link')
            .attr('stroke', d => this.linkColorScale(d.type))
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', 1)
            .attr('marker-end', 'url(#arrowhead)');
    }

    /**
     * Create link labels
     */
    createLinkLabels() {
        if (!this.options.showLabels) return;

        this.linkLabelElements = this.g.append('g')
            .attr('class', 'graph-link-labels')
            .selectAll('text')
            .data(this.links)
            .enter()
            .append('text')
            .attr('class', 'graph-link-label')
            .text(d => d.type)
            .attr('dy', -5);
    }

    /**
     * Create node elements
     */
    createNodes() {
        this.nodeElements = this.g.append('g')
            .attr('class', 'graph-nodes')
            .selectAll('circle')
            .data(this.nodes)
            .enter()
            .append('circle')
            .attr('class', 'graph-node')
            .attr('r', d => this.calculateNodeRadius(d))
            .attr('fill', d => this.nodeColorScale(d.type))
            .call(this.dragBehavior())
            .on('click', (event, d) => this.handleNodeClick(event, d))
            .on('mouseover', (event, d) => this.handleNodeMouseOver(event, d))
            .on('mouseout', (event, d) => this.handleNodeMouseOut(event, d));
    }

    /**
     * Create node labels
     */
    createNodeLabels() {
        if (!this.options.showLabels) return;

        this.nodeLabelElements = this.g.append('g')
            .attr('class', 'graph-node-labels')
            .selectAll('text')
            .data(this.nodes)
            .enter()
            .append('text')
            .attr('class', 'graph-node-label')
            .text(d => this.truncateLabel(d.name, 15))
            .attr('dy', 4);
    }

    /**
     * Calculate node radius based on properties
     * @param {object} node - Node data
     * @returns {number} Radius
     */
    calculateNodeRadius(node) {
        const baseRadius = this.options.nodeRadius;
        const degree = node.properties?.degree || 1;
        return Math.min(20, Math.max(baseRadius, baseRadius + Math.sqrt(degree)));
    }

    /**
     * Truncate label text
     * @param {string} text - Original text
     * @param {number} maxLength - Maximum length
     * @returns {string} Truncated text
     */
    truncateLabel(text, maxLength) {
        if (!text) return '';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    /**
     * Simulation tick function
     */
    ticked() {
        if (this.linkElements) {
            this.linkElements
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
        }

        if (this.linkLabelElements) {
            this.linkLabelElements
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);
        }

        if (this.nodeElements) {
            this.nodeElements
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
        }

        if (this.nodeLabelElements) {
            this.nodeLabelElements
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        }
    }

    /**
     * Create drag behavior
     * @returns {function} Drag behavior function
     */
    dragBehavior() {
        const dragStarted = (event, d) => {
            if (!event.active) this.simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        };

        const dragged = (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
        };

        const dragEnded = (event, d) => {
            if (!event.active) this.simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        };

        return d3.drag()
            .on('start', dragStarted)
            .on('drag', dragged)
            .on('end', dragEnded);
    }

    /**
     * Handle node click
     * @param {object} event - Click event
     * @param {object} d - Node data
     */
    handleNodeClick(event, d) {
        // Highlight connected nodes and links
        const connectedLinks = this.links.filter(l =>
            l.source.id === d.id || l.target.id === d.id
        );

        const connectedNodeIds = new Set();
        connectedLinks.forEach(l => {
            if (l.source.id !== d.id) connectedNodeIds.add(l.source.id);
            if (l.target.id !== d.id) connectedNodeIds.add(l.target.id);
        });

        // Reset all opacity
        this.nodeElements.style('opacity', 0.2);
        this.linkElements.style('opacity', 0.1);
        if (this.nodeLabelElements) this.nodeLabelElements.style('opacity', 0.2);
        if (this.linkLabelElements) this.linkLabelElements.style('opacity', 0.1);

        // Highlight selected node
        d3.select(event.currentTarget).style('opacity', 1);
        if (this.nodeLabelElements) {
            this.nodeLabelElements.filter(n => n.id === d.id).style('opacity', 1);
        }

        // Highlight connected nodes and links
        connectedNodeIds.forEach(nodeId => {
            this.nodeElements.filter(n => n.id === nodeId).style('opacity', 1);
            if (this.nodeLabelElements) {
                this.nodeLabelElements.filter(n => n.id === nodeId).style('opacity', 1);
            }
        });

        connectedLinks.forEach(link => {
            this.linkElements.filter(l => l === link).style('opacity', 1);
            if (this.linkLabelElements) {
                this.linkLabelElements.filter(l => l === link).style('opacity', 1);
            }
        });

        // Show node details (could trigger modal or callback)
        this.showNodeDetails(d);
    }

    /**
     * Handle node mouseover
     * @param {object} event - Mouse event
     * @param {object} d - Node data
     */
    handleNodeMouseOver(event, d) {
        const tooltipContent = `
            <strong>${d.name}</strong><br>
            Type: ${d.type}<br>
            ${d.source_document ? `Document: ${d.source_document}<br>` : ''}
            ${d.confidence ? `Confidence: ${(d.confidence * 100).toFixed(1)}%<br>` : ''}
            <small>Click for details</small>
        `;

        this.tooltip.html(tooltipContent)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 10) + 'px')
            .style('display', 'block');
    }

    /**
     * Handle node mouseout
     */
    handleNodeMouseOut() {
        this.tooltip.style('display', 'none');
    }

    /**
     * Show node details (placeholder - could be extended)
     * @param {object} node - Node data
     */
    showNodeDetails(node) {
        // This could trigger a modal or callback
        console.log('Node details:', node);
        // Example: dispatch custom event
        const event = new CustomEvent('graph-node-click', { detail: node });
        this.container.dispatchEvent(event);
    }

    /**
     * Show empty state
     */
    showEmptyState() {
        this.g.append('text')
            .attr('x', this.options.width / 2)
            .attr('y', this.options.height / 2)
            .attr('text-anchor', 'middle')
            .attr('class', 'text-muted')
            .text('No graph data available');
    }

    /**
     * Get node color scale
     * @returns {d3.scaleOrdinal} Node color scale
     */
    getNodeColorScale() {
        return this.nodeColorScale;
    }

    /**
     * Get link color scale
     * @returns {d3.scaleOrdinal} Link color scale
     */
    getLinkColorScale() {
        return this.linkColorScale;
    }

    /**
     * Get unique entity types
     * @returns {Array} Entity types
     */
    getEntityTypes() {
        return [...new Set(this.nodes.map(d => d.type))];
    }

    /**
     * Get unique relationship types
     * @returns {Array} Relationship types
     */
    getRelationshipTypes() {
        return [...new Set(this.links.map(d => d.type))];
    }

    /**
     * Update legend (external legend in HTML)
     */
    updateLegend() {
        // This method is called from external code after render
        // The legend is managed by the parent component
    }

    /**
     * Zoom in
     */
    zoomIn() {
        this.svg.transition().call(this.zoom.scaleBy, 1.3);
    }

    /**
     * Zoom out
     */
    zoomOut() {
        this.svg.transition().call(this.zoom.scaleBy, 0.7);
    }

    /**
     * Reset zoom and pan
     */
    resetZoom() {
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity);
    }

    /**
     * Center graph
     */
    centerGraph() {
        if (!this.simulation || this.nodes.length === 0) return;

        // Calculate bounds
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
        this.nodes.forEach(node => {
            if (node.x < minX) minX = node.x;
            if (node.x > maxX) maxX = node.x;
            if (node.y < minY) minY = node.y;
            if (node.y > maxY) maxY = node.y;
        });

        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;
        const scale = Math.min(
            this.options.width / (maxX - minX || 1),
            this.options.height / (maxY - minY || 1)
        ) * 0.8;

        const transform = d3.zoomIdentity
            .translate(this.options.width / 2, this.options.height / 2)
            .scale(scale)
            .translate(-centerX, -centerY);

        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, transform);
    }

    /**
     * Update container size
     */
    resize() {
        this.options.width = this.container.clientWidth;
        this.options.height = this.container.clientHeight;

        if (this.svg) {
            this.svg
                .attr('width', this.options.width)
                .attr('height', this.options.height);
        }

        if (this.simulation) {
            this.simulation.force('center', d3.forceCenter(
                this.options.width / 2,
                this.options.height / 2
            ));
            this.simulation.alpha(0.3).restart();
        }
    }

    /**
     * Destroy instance and clean up
     */
    destroy() {
        if (this.simulation) {
            this.simulation.stop();
            this.simulation = null;
        }

        if (this.svg) {
            this.svg.selectAll('*').remove();
            this.svg = null;
        }

        this.nodes = [];
        this.links = [];
    }
}

// Make GraphPreview globally available
if (typeof window !== 'undefined') {
    window.GraphPreview = GraphPreview;
}